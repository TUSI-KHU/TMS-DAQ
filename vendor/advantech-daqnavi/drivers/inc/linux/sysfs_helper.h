/*
 * sysfs_helper.h
 *
 *  Created on: 2011-11-25
 *      Author: rocky
 */
/*XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
 *                   !!!CAUTION!!!
 *        !!!ONLY INCLUDE THIS FILE IN ONE .c file!!!
 XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX*/
#ifndef DAQNAVI_SYSFS_HELPER_H
#define DAQNAVI_SYSFS_HELPER_H

static ssize_t daq_sysfs_show_desc(struct device *dev, struct device_attribute *attr, char *buf)
{
#ifdef DEV_NAME
   daq_device_t *daq_dev = (daq_device_t *)dev_get_drvdata(dev);
   return sprintf(buf, "%s,BID#%d", DEV_NAME(&daq_dev->kshared), daq_dev->kshared.board_id);
#elif defined(DEVICE_NAME_FROM_PID)
   daq_device_t *daq_dev = (daq_device_t *)dev_get_drvdata(dev);
   return sprintf(buf, "%s,BID#%d", DEVICE_NAME_FROM_PID(daq_dev->shared.ProductId), daq_dev->shared.BoardId);
#elif defined(DEVICE_NAME)
   daq_device_t *daq_dev = (daq_device_t *)dev_get_drvdata(dev);
   return sprintf(buf, DEVICE_NAME",BID#%d", daq_dev->shared.BoardId);
#else
   return sprintf(buf, DEVICE_DESC);
#endif
}
  
static ssize_t daq_sysfs_show_drvname(struct device *dev, struct device_attribute *attr, char *buf)
{
#ifdef DRV_NAME
   return sprintf(buf, DRV_NAME);
#else 
   return sprintf(buf, DRIVER_NAME);
#endif
}

static DEVICE_ATTR(desc,    S_IRUGO, daq_sysfs_show_desc,    NULL);
static DEVICE_ATTR(drvname, S_IRUGO, daq_sysfs_show_drvname, NULL);

static struct attribute *dev_attrs[] = {
   &dev_attr_desc.attr,
   &dev_attr_drvname.attr,
   NULL
};

static const struct attribute_group attr_group = {
   .attrs = dev_attrs,
};

static struct device * daq_sysfs_dev_create(dev_t devid, void *daq_dev)
{
#  if (LINUX_VERSION_CODE < KERNEL_VERSION(2,6,27))
   struct device *sysfs = device_create(daq_class_get(), NULL, devid, "daq""%d", MINOR(devid));
#  else
   struct device *sysfs = device_create(daq_class_get(), NULL, devid, daq_dev, "daq""%d", MINOR(devid));
#  endif

   if (!IS_ERR(sysfs)) {                                     
      dev_set_drvdata(sysfs, daq_dev);                
      if (sysfs_create_group(&sysfs->kobj, &attr_group) < 0) {
         dev_warn(sysfs, "attr group create failed\n");             
      }

      sysfs->driver = daq_class_drv_get();         
#  if (LINUX_VERSION_CODE < KERNEL_VERSION(2,6,19))
      device_bind_driver(sysfs);
#  else
      if (device_bind_driver(sysfs)) {
         dev_warn(sysfs, "bind driver failed\n");              
      }
#  endif
   }      

   return sysfs;        
}

static void daq_sysfs_dev_destroy(struct device *sysfs)
{
   if (!IS_ERR(sysfs)) {   
      sysfs_remove_group(&sysfs->kobj, &attr_group);
      
      if (sysfs->driver) {
         device_release_driver(sysfs);
      }

      device_destroy(daq_class_get(), sysfs->devt);
   }
}

#endif /* DAQ_SYSFS_DEF_H_ */
