appengine-thumbnails
====================

Concept inspired by Simon Willison's Resize Proxy (https://github.com/simonw/resize-proxy). This is actively used at Mixcloud in production, and has enabled the team to rapidly change the UI whilst scaling out the image system.

Set BASE_URL to your origin servers, and set the dimensions allowed. Then deploy to appengine

Images are now available on urls such as 

http://thumb1.mixcloud.com/w/50/h/50/q/85/upload/images/extaudio/34660919-cbf4-421a-8820-22a4fab7e3b8.jpeg

Also fixed width images can be generated using

http://thumb1.mixcloud.com/w/50/q/85/upload/images/extaudio/34660919-cbf4-421a-8820-22a4fab7e3b8.jpeg

It is recommended that you setup payments for appengine, as this will enable a varnish cache even if you don't go above the free quota's, speeding up the requests.

