
import cickle


filename = "/home/justin/scans/s14_dti.pickle"
pickle_file = open(filename, 'r')
picklist1 = cPickle.load(pickle_file)
print picklist1
