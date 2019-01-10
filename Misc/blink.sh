#!/usr/bin/env bash

SUBJ=001
subj_start() {
	blink=$(tput blink)$(tput setaf 1)
  	normal=$(tput sgr0)
  SUBJ_F=${blink}${SUBJ}${normal}
	printf "\\n%s" "///////////////////////////////////////////"
	printf "\\n%s" "//-----------NOW PRE-PROCESSING----------//"
  	printf "\\n%s" "//----------------SUBJECT #--------------//"
	printf "\\n%s" "//------------------$SUBJ_F------------------//"
	printf "\\n%s\\n" "///////////////////////////////////////////"
}

subj_start
