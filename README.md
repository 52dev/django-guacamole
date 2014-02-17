django-guacamole
================
Proof-of-concept integration between django and guacamole.

Setup
-----
1. Point settings.GUACD_HOST and settings.GUACD_PORT to the location of the guacd daemon.
2. Update the host information in the ```_do_connect``` method in views.py to point to the machine to login into.
