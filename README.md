# Site Wrangler

Site Wrangler is an nginx-based webserver management system for Debian/Ubuntu aimed at independant web developers. nginx is usually backed by PHP-FPM sockets; however, Site Wrangler allows you to freely customize your nginx configuration files, giving you the power to serve any way you want. For email, Site Wrangler uses and configures Exim and Dovcot.

Site Wrangler does not override your configuration files except where noted and does not run it’s own daemon on the server. It provides a command line interface to automate the tedious processes of managing your own configuration files.

Site Wrangler is currently in a pre-release state and as such, updating Site Wrangler to a newer version may require updating some configuration files by hand. Because of this, it is suggested to migrate to a fresh install rather than update Site Wrangler until version 1.0 is released.

## Core Concepts

Site Wrangler is only tested on Ubuntu and Debian at this time but aims to eventually be compatible with as many Unix and Unix-like systems as possible. If you are not using Site Wrangler for email, it currently also supports CentOS 7 and 8.

### The Installers

Site Wrangler comes with two install scripts; one for email and one for the web. Each installs the appropriate prerequisites on the base system. These installers are the most OS-dependent part of Site Wrangler. Most system administrators with Bash experience should be able to adapt the installers to fit systems they have experience with.

### The Build System

One of the highlights of Site Wrangler is the extensible source build system. Site Wrangler updates, compiles and builds OpenSSL and the web software that depends on it like PHP and nginx. This allows the system to be continually updated with the latest software fixes and features. Site Wrangler uses vanilla source code to maintain consistency across systems. Site Wrangler also allows you to customize the configuration arguments that are used at build time for each software package allowing for full customization of web services. For more information on the build system, see the longer guide.

### Webserver

Site Wrangler uses nginx with ModSecurity as a webserver and/or proxy. When you create a site configuration file for nginx, you can use a number of configuration templates. This allows you to quickly deploy and manage both custom and off-the-shelf sites.

Each site must be assigned to a unique system user.

Let’s Encrypt is used to fetch certificates for each site. The default rules within each nginx vhost template file allow for nginx to handle Let’s Encrypt’s site verification traffic directly. This allows nginx to proxy to web applications that may not be otherwise compatible with HTTPS or Let’s Encrypt. There is also an option to have a copy of the current certificate for a site be placed within the system user’s home directory. This allows custom applications to make use certificates outside of nginx.

### Email

Site Wrangler uses Dovecot for IMAP and POP (checking your email). Dovecot is configured to allow the use of SpamAssassin to filter messages for individual email accounts or on domains as a whole. Exim is used for SMTP (sending and receiving email) and relies on Dovecot to authenticate outgoing emails.

Email accounts are set up in a similar manner to those in cPanel. Email messages are stored in the “mail” subfolder within the system user’s home directory, while email configuration files are stored in the “etc” subfolder. Within each of those folders is a directory named after the email domain and within that, one named after the user. By default, the server uses Maildir format to store messages. The default configuration also makes use of DKIM, SPF and DMARC to protect from email fraud such as spoofing.

### Separation of Site Files

All configurations that are site-specific are split out into separate configuration files. For DNS, this comes in the usual zone files. For nginx and PHP, this means each site gets it’s own vhost file. This makes management of the sites easier. For example, each of these systems can simply add “.disabled” to the end of the filename to disable but not delete a site.

### Firewall

Site Wrangler uses CSF firewall for integration with ModSecurity and email services. The firewall configuration that comes with Site Wrangler allows traffic only on ports for HTTP (80), HTTPS (443), secure IMAP (993), secure POP (995), SMTP (25), and secure SMTP (465).

Notably absent are SSH, non-secure IMAP, and non-secure POP. There is no reason to support insecure mail logins in this day and age. For SSH access, IP addresses should be whitelisted individually. Opening SSH is of coarse possible, however switching SSH to a non-standard port is strongly recommended if it is to be opened to the public.
