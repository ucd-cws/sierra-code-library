##accumulation Stats
library(foreign)
setwd("C:/Users/nrsantos/Desktop/forTed")
var <- read.csv("C:/Users/nrsantos/Desktop/forTed/HUC12_fv_exp.csv", header=T)
str(var)

hct <- read.csv("C:/Users/nrsantos/Dropbox/Public/Temp/Connectivity/HUC_Connectivity.csv", header=T)
#cor.hucs <- read.dbf("D:/PRISM/Freshwater_Extraction/HUC12s/Corrected_ca_table.dbf")

##---------------------------------------upstream function---------------------------------------##

upstream <- function(id){
  temp<-subset(hct, hct$ZoneD==as.numeric(id))
  uphucs<<-c(unique(temp$ZoneU),id)
}

##------------------------Compute upstream statistics and Merge datasets-------------------------##
  
  results <- data.frame()
  
  #for (i in unique(var$HUC_12)) {
  for (i in var$HUC_12) {

    if(i %in% unique(hct$ZoneD)){ 
      upstream(i)
      var.sub <- subset(var, var$HUC_12 %in% uphucs)
      FV_sum <- sum(var.sub$FV_sum)
      POD_count <- sum(var.sub$POD_count)
      MAXUSE_sum <- sum(var.sub$MAXUSE_sum)
      MAXSTO_sum <- sum(var.sub$MAXSTO_sum)
      ushucs <- length(uphucs)-1}
    
    else{var.single <- subset(var, var$HUC_12 == i)
         FV_sum <- sum(var.single$FV_sum)
         POD_count <- sum(var.single$POD_count)
         MAXUSE_sum <- sum(var.single$MAXUSE_sum)
         MAXSTO_sum <- sum(var.single$MAXSTO_sum)
         ushucs <- 0}
    print(paste("id:",i,"Upstream HUCs:",ushucs))
    tem <- data.frame(HUC_12 = i, US_HUCs = ushucs, FV_sum_sum = FV_sum, POD_count_sum = POD_count,  MAXUSE_sum_sum =  MAXUSE_sum, MAXSTO_sum_sum = MAXSTO_sum)
    #colnames(tem) <- c("HUC_12", var.name)
    results <- rbind(results,tem)
  }

write.csv(results, "HUC12_fv_sum_all.csv", row.names=F)
#write.csv(results, "HUC12_fv_sum_unique.csv", row.names=F)

length(var$HUC_12)-length(unique(var$HUC_12))
var$HUC_12

length(var$HUC_12)-length(unique(var$HUC_12))