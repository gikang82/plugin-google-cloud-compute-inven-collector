# plugin-googlecloud-compute
![Google Cloud Compute](https://spaceone-custom-assets.s3.ap-northeast-2.amazonaws.com/console-assets/icons/cloud-services/google_cloud/Google_Cloud.svg)
**Plugin for Google Cloud Compute Engine VM servers**

> SpaceONE's [plugin-google-cloud-compute](https://github.com/spaceone-dev/plugin-google-cloud-compute) is a convenient tool to 
extract Compute Engine VMs data from Google Cloud platform. 


Find us also at [Dockerhub](https://hub.docker.com/repository/docker/spaceone/google-cloud-compute)
> Latest stable version : 1.2.5

Please contact us if you need any further information. (<support@spaceone.dev>)

---

## Authentication Overview
Registered service account on SpaceONE must have certain permissions to collect cloud service data 
Please, set authentication privilege for followings:

### Contents

* Table of Contents
    * [Compute Engine](#compute-engine)
        * [Compute VM (Instance)](#compute-vminstance)
       
---

#### [Compute Engine](https://cloud.google.com/compute/docs/apis)

- ##### Compute VM (Instance)
    - Scopes
        - https://www.googleapis.com/auth/compute
        - https://www.googleapis.com/auth/cloud-platform
        
    - IAM
        - compute.zones.list
        - compute.regions.list
        - compute.instances.list
        - compute.machineTypes.list
        - compute.urlMaps.list
        - compute.backendServices.list
        - compute.disks.list
        - compute.diskTypes.list
        - compute.autoscalers.list
        - compute.images.list
        - compute.subnetworks.list
        - compute.regionUrlMaps.list
        - compute.backendServices.list
        - compute.targetPools.list
        - compute.forwardingRules.list