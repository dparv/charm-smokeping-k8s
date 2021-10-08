#!/bin/sh
/bin/ln -s /usr/share/webapps/smokeping /var/www/localhost
/bin/chown -R abc:abc /usr/share/webapps/smokeping
/bin/chown -R abc:abc /var/www/localhost/smokeping
/bin/ln -s /var/cache/smokeping /usr/share/webapps/smokeping/cache
/bin/ln -s /var/lib/smokeping/.simg /usr/share/webapps/smokeping/img
/bin/sh /usr/sbin/apachectl -D FOREGROUND
