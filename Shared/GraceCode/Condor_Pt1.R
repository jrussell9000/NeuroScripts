###############################
#Title: "Part 1 Condor sCCA"
#Author: Grace George, adapted from Cedric Huchuan Xia
#Date 9/22/21
#This script is  part 1 for use on ABCD data for Condor.  


##############################
#Load Packages

library('tidyverse')
library('caret')
library('stringr')
library('ggplot2')
library('cowplot')
library('lmSupport')
library('rasterVis')
library('parallel')
library('PMA')
library('Matrix')
library('emdbook')
library('R.matlab')
library('MASS')
library('permute')
library('matrixStats')
library('scales')
source('C:/Users/gcgeorge/Desktop/pconn_csv/cca_functions.R')
##############################
#Load data
library(data.table)
#Txt files for clinical data and demographic data
clin_data <- fread("C:/Users/gcgeorge/Desktop/pconn_csv/abcd_cbcl01_new.txt", header = TRUE)
demo <- read.table("C:/Users/gcgeorge/Desktop/pconn_csv/abcddemo01.txt", header = TRUE)


#Merge data and keep only the things we want. remove NAs 

go1data <- merge(clin_data,demo, by = "subjectkey")
go1data <-  go1data %>%
  drop_na()
#Use this for the actual one
neuroid <- list.files(path = "C:/Users/gcgeorge/Desktop/pconn_csv/", pattern = "sub-*" )


neuroid_mat <- data.frame(neuroid)
neuroid_mat$subjectkey <- str_sub(neuroid_mat$neuroid, 5, 19)
go1data$subjectkey <- gsub("_", "", as.character(go1data$subjectkey))

go1data$neuro <- ifelse(go1data$subjectkey %in% neuroid_mat$subjectkey,1,0)

#Final list for data. Must match a scan and must be baseline year 1
final_clinical <- go1data %>%
  filter(neuro == 1 & eventname.x == c("baseline_year_1_arm_1"))

#get list for final neuro people
neuroid_mat$clin <- ifelse(neuroid_mat$subjectkey %in% final_clinical$subjectkey,1,0)

final_neuro_temp <- neuroid_mat %>%
  filter(clin == 1)


LabelList <- read.table("C:/Users/gcgeorge/Desktop/pconn_csv/Schaefer2018_400Parcels_7Networks_order_Tian_Subcortex_S4_label_reformatted.txt", header = FALSE, sep="\t")
#Make a vector with the column names
Labels <- LabelList[,2]

data_path <- "C:/Users/gcgeorge/Desktop/pconn_csv/Final_sample/"

temp_list <- as.table(as.matrix(final_neuro_temp$subjectkey))
n_sample <- dim(temp_list)[1]
sample_net<-array(NA, c(454, 454, n_sample))
for (i in 1:n_sample){
  scanid <- temp_list[i]
  netpath <-  paste0(data_path,scanid,".pconn.nii.csv")
  sample_net[,,i] <- as.matrix(read.csv(netpath))
  print(paste(i,"."," copying ",scanid,sep=""))
}

net_ft <-t(apply(sample_net,c(3),function(x) x[upper.tri(x, diag = F)]))
rownames(net_ft) <- final_neuro_temp$subjectkey

power_mad<- apply(net_ft,2,function(x) round(mad(x),digits=4))

# plot the edge variation 
#put in order the edges
power_mad_order <- data.frame(numedge = as.factor(1:dim(net_ft)[2]),mad = power_mad[order(-power_mad)])
#put them in quantiles
salient_percent <- c(quantile(power_mad,c(.95,.9,.75,.5),na.rm = T))
#threshold greater than each of the percentages
thresh <- c(1,sapply(seq_along(salient_percent),function(i) round(mean(which(power_mad_order$mad == salient_percent[i])))), dim(net_ft)[2])
#groups them by what percintle group they are in
power_mad_order$group <- as.factor(c(rep(1,thresh[2]),rep(2,thresh[3]-thresh[2]),rep(3,thresh[4]-thresh[3]),rep(4,thresh[5]-thresh[4]),rep(5,thresh[6]-thresh[5])))

Threshold <- thresh[2]
#compile the features
# Take the edges with top 10% MAD
inc_idx <- which(power_mad>= power_mad_order$mad[Threshold])
inc_net <- net_ft[,inc_idx]

final_clinical$gender.x <- as.factor(final_clinical$gender.x)
final_clinical$interview_age.x <- as.factor(final_clinical$interview_age.x) #SHOULD I DO AGE?
final_neuro_temp$gender.x <- final_clinical$gender.x
final_neuro_temp$interview_age.x <- final_clinical$interview_age.x
#regress out covariates

power.rgr <- matrix(NA, nrow = dim(inc_net)[1], ncol = dim(inc_net)[2])
rownames(power.rgr) <- rownames(net_ft)
power.rgr <- apply(inc_net, 2, function(x) residuals.glm(glm(x ~  
                                                               gender.x + interview_age.x , data = final_neuro_temp), type = "response"))

med <- final_clinical
###GOing to leave in the Subj id right now.
med.torgr <- within(med, rm("subjectkey"))
rownames(med.torgr) <- med$subjectkey
#Redo gender so it is binary numeric and remove 1st column
med.torgr$gender.x <- varRecode(med.torgr$gender.x, c("M", "F"), c("-.5", ".5"))
med.torgr$interview_age.x <- as.numeric(med.torgr$interview_age.x)
med.torgr <- med.torgr %>%
  dplyr::select(c(9:127)) %>%
  mutate_if(is.character,as.numeric)
med.torgr$gender.x <- med$gender.x
med.torgr$interview_age.x <- med$interview_age.x

med.rgr <- apply(med.torgr[,1:119], 2, function(x) residuals.glm(glm(x ~ interview_age.x + 
                                                                       gender.x , data = final_clinical ), type = "response"))
#regress out the binary variables (everything else) Dont have any binary in med
rownames(med.rgr) <- med$subjectkey
#colnames(med.rgr) <- colnames(med.torgr)
pwr_med_rgr <- med.rgr

###Visualizing features
#any column that isn't above the 10% threshold make NA
net_ft[,-inc_idx] <- NA

power.data <- net_ft

#Make an array to put the features i need in it
power.cln.aj <- array(NA, c(454,454,dim(power.data)[1]))
#for every feature created, takes the upper part of the matrix and makes it symmetrical??  Then paste it into the array
for (i in 1:dim(power.data)[1]) {
  tempmax <- power.cln.aj[ , ,i]
  tempmax[upper.tri(tempmax,diag=F)] <- as.numeric(power.data[i,])
  tempmax <- sna::symmetrize(tempmax,rule='upper')
  power.cln.aj[ , , i] <- tempmax
  print(paste('No.',i,'subject'))
}
#then take what you just made, and remove all Nas so its a clean
power.cln.ave <- apply(power.cln.aj, c(1,2), function(x) mean(na.omit(x)))
#plot it out!
levelplot(power.cln.ave, at = seq(-0.5,0.5,length=10),xlab='',ylab='',main="Power Train Set")
pwr.3k.pos.ave <- power.cln.ave
pwr.3k.pos.idx <- inc_idx

#loading residuals from neuroimaging
net.data <- unname(power.rgr)
#Loading residuals from clinical 
med.data <- unname(pwr_med_rgr)
#gettting rid of columns with zeros because CCA unhappy. Take this out before actually running
load('C:/Users/gcgeorge/Desktop/pconn_csv/med.data.RData')
load('C:/Users/gcgeorge/Desktop/pconn_csv/net.data.RData')
Med_data <- read.csv("C:/Users/gcgeorge/Desktop/pconn_csv/med_data.csv")
med.data <- med.data[, colSums(med.data != 0) > 0]
#makes a list of two matrixes
data <- list(brain = net.data, behavior = med.data)
print(paste("Training sample has",dim(net.data)[1],"subjects."))
print(paste("rsFC data has",dim(net.data)[2],"edges."))
print(paste("clinical data has",dim(med.data)[2],"items."))

#create sample splits
#Come back to this later
#load("./projects/xiaNetworkCca/sCCA/aim1/result/201701/pwr_pos_qa.RData")
#pretty sure this is loading the clinical ids
subjid <- Med_data
sampleid <- createDataPartition(subjid$subjectkey, p = 1, list =T,times=1)
#parallelizes putting the IDs on each one
brain_sample <- mclapply(sampleid, function(subjectkey) data$brain[subjectkey,])
behavior_sample <- mclapply(sampleid, function(subjectkey) data$behavior[subjectkey,])
#brain_sample <- net.data
#behavior_sample <- med.data

#select parameters for regularization

x_pen <- seq(0.1,1,length.out=10)
y_pen <- seq(0.1,1,length.out=10)
load('C:/Users/gcgeorge/Desktop/pconn_csv/brain_sample.RData')
load('C:/Users/gcgeorge/Desktop/pconn_csv/behavior_sample.RData')

scca.gs <- ccaDWfoldgs(brain_sample,behavior_sample,x_pen,y_pen)
gs.mat <- matrix(scca.gs$GS[,'COR_MEAN'], nrow = 10, ncol = 10)
rownames(gs.mat) <- x_pen
colnames(gs.mat) <- y_pen

png(filename = "reg_parameters.png")
image(gs.mat)
dev.off()

modenum <- dim(data$behavior)[2] #number of all possible canonical variates
scca.org <- ccaDW(data$brain, data$behavior,0.4,0.3,modenum) #0.8 and 0.4 here are the best parameteres selected above in the grid search  CHECK THIS
brain_std <- apply(data$brain,2,scale) #make sure data are demeaned
med_std <- apply(data$behavior,2,scale)
covmat <- t(scca.org$u) %*% t(brain_std) %*% med_std %*% scca.org$v #calculate covariance matrix
varE <- diag(covmat)^2 / sum(diag(covmat)^2) #calculate covariance explained by each component
varE.df <- data.frame(modenum = as.factor(1:modenum), var = varE) #prepare dataframe for plotting

candnum = 5 #number selected based on the scree plot
p.var<-ggplot(varE.df,aes(modenum,var)) +
  geom_point(stat = 'identity',aes(color = var > varE[candnum+1], size = var)) +
  geom_hline(yintercept = 1/modenum,linetype="dashed") +
  scale_x_discrete(name ="Mode", limits=c(0:modenum),breaks =  c(1,seq(10,modenum,10))) +
  scale_y_continuous(expand = c(0, 0),limits=c(0,0.075),labels = percent,name = "Variance Explained", breaks=seq(0,0.075,length=4)) +
  theme_classic(base_size = 20) +
  theme(legend.position = 'none') 
p.var

#rUN THE SCCA :)

scca.cand <- ccaDW(data$brain, data$behavior,0.4,0.3,candnum)
scca.cca <- mclapply(seq_along(sampleid),function(i) ccaDW(brain_sample[[i]],behavior_sample[[i]],0.4,0.3,20)) #loop through split
#takes a long time
scca.cca.ro <- sapply(scca.cca,function(x) reorderCCA(x,scca.cand,20)) #reorder the component so they match across splits
#takes a long time
scca.cca.cor <- rowMeans(simplify2array(scca.cca.ro['cors',]),na.rm =T) #calculate average of cca correlations
scca.cca.cor.se <- rowSds(simplify2array(scca.cca.ro['cors',]),na.rm =T)/sqrt(dim(scca.cca.ro)[2]) #calculate standard error of correlations
std_mean <- function(x) sd(x)/sqrt(length(x))
scca.cca.cor.se <- std_mean(simplify2array(scca.cca.ro['cors',]))
#plot the correlation

cor.df <- data.frame(modenum = as.factor(1:candnum), cor = scca.cca.cor, se = scca.cca.cor.se)
cor.df.order <- cor.df[order(-cor.df$cor),]
cor.lim <- aes(ymax = cor.df.order$cor + cor.df$se, ymin = cor.df.order$cor - cor.df$se)
p.cor <- ggplot(cor.df.order,aes(1:length(modenum), cor, label = round(cor,2))) +
  geom_bar(width = 0.75, stat = 'identity',  fill = '#00BFA5') +
  geom_errorbar(cor.lim,  width=0.25) +
  geom_text(size = 4, position = position_dodge(width = 0.9), vjust= -1,color='grey')+
  scale_x_discrete(name ="Mode", limits=c(1:candnum) ) +
  scale_y_continuous(expand = c(0, 0),limits=c(0,0.8),name = "CCA Correlation", breaks=seq(0,0.8,length=5)) +
  theme_classic(base_size = 20) +
  coord_cartesian(ylim=c(0.02,0.3)) +
  theme(legend.position = 'none') 
p.cor

#permutation test
num.perm <- 1000 #number of permutaitons to run
behavior.perm <- rlply(num.perm,data$behavior[sample(nrow(data$behavior)),]) #permute the clinical matrix by row
#takes a long time
scca.perm.cca<-sapply(behavior.perm, function(y_perm){ out<-ccaDWpermorder(data$brain,y_perm,0.4,0.3,candnum,scca.cand)} ) #run scca again with permuted clinical but with original connectivity
#load("~/Desktop/BBL/projects/xiaNetworkCca/sCCA/aim1/result/201701/pwr_perm_cca.RData")
perm.cor <- simplify2array(scca.perm.cca['cors',]) #extract the correlations
perm.pval <- sapply(seq_along(cor.df$cor),function(x) (length(which(perm.cor[x,] >= cor.df$cor[x])) ) / length(which(is.na(perm.cor[x,]) == FALSE))) #calcualte the empirical p-val

#plot the permutation test
perm.cor.df <- as.data.frame(t(perm.cor))
perm.pass <- which(perm.pval < 0.05)
permplots <-lapply(perm.pass,function(x) perm.plot(perm.cor.df,cor.df,perm.pval,x))

#bootstrap which features are the most important?

#load("./projects/xiaNetworkCca/sCCA/aim1/result/201701/scca_boot1000.RData")
#load('./projects/xiaNetworkCca/sCCA/aim1/result/201701/scca_noreg_boot1.RData')
#load('./projects/xiaNetworkCca/sCCA/aim1/result/201701/scca_noreg_boot2.RData')
#scca.boot <- append(scca.noreg.boot1,scca.noreg.boot2)

#save(perm.pass,file ="./perm.pass.RData")
#save(subjid,file ="./subjid.RData")
#save(data,file ="./data.RData")
#save(scca.cand,file ="./scca.cand.RData")

###COME BACK TO THIS 10/5/21
bootnum = 10 #number of bootstraps to run (try 10)
bootid <- createResample(subjid$subjectkey, list = T, times = bootnum) #create lists of subjs for bootstrap
brain_boot <- lapply(bootid, function(id) data$brain[id,]) #create bootstrap samples for connectivity features
behavior_boot <- lapply(bootid, function(id) data$behavior[id,]) #create bootstrap samples for clinical features
#scca.boot<- mclapply(seq_along(bootid),function(i) ccaDW(brain_boot[[i]],behavior_boot[[i]],0.8,0.4,10),mc.cores = 5) #run scca on these bootstrap sample
scca.boot <- mclapply(seq_along(bootid),function(i) ccaDW(brain_boot[[i]],behavior_boot[[i]],0.4,0.3,10)) #run scca on these bootstrap sample
scca.boot.ro <- lapply(1:bootnum,function(i) reorderCCA(scca.boot[[i]],scca.cand,10)) #reorder to match components across samples
scca.boot.u <- lapply(perm.pass, function(x) sapply(1:bootnum, function(i) scca.boot.ro[[i]]$u[,x])) #extract loadings on connectivity features
scca.boot.v <- lapply(perm.pass, function(x) sapply(1:bootnum, function(i) scca.boot.ro[[i]]$v[,x])) #extract loadings on clinical features
#scca.boot.cor <-  sapply(1:1000, function(i) scca.boot.ro[[i]]$cor)
u.boot.plot <- lapply(seq_along(perm.pass), function(x) bootplot_u(scca.cand$u[,perm.pass[x]], scca.boot.u[[x]] ))  #apply 99.5% confidence interval
v.boot.plot <- lapply(seq_along(perm.pass), function(x) bootplot(scca.cand$v[,perm.pass[x]], scca.boot.v[[x]] )) #apply 95% confidence interval

#Get important clinical features
#load("./projects/xiaNetworkCca/sCCA/aim1/data/med_item_annotation.RData") #load clinical question
dim.match <- sapply(seq_along(1:length(perm.pass)), function(x) which(perm.pass == cor.df.order$modenum[x])) 
med.plots.nt <- lapply(seq_along(1:length(dim.match)), function(x) med_vis(v.boot.plot[[dim.match[x]]], "")) #plot the clinical features over CI95%
med.plots.grid <- plot_grid(plotlist = med.plots.nt,labels = c("A","B","C","D"))
#save_plot("./projects/xiaNetworkCca/sCCA/aim1/figure/201701/med_plots_norgr.pdf",med.plots.grid,base_height = 14,base_aspect_ratio = 1.3)

#get brain dimensions and plot
load('C:/Users/gcgeorge/Desktop/pconn_csv/pwr.3k.idx.RData')
sign.match <- sign(colMeans(sign(scca.cand$v[,perm.pass[dim.match]])))
sign.match <- c(1,3)
brain.plots <- lapply(seq_along(1:length(dim.match)), function(x) brain_vis(u.boot.plot[[dim.match[x]]] ,paste("Dimension",x),sign.match[x],pwr.3k.idx,V_Matrix)) #visualize the brain loadings


                            