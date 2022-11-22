<?php
/**
* Plugin Name: Site Wrangler Login Security
* Plugin URI: https://sitewrangler.org/
* Description: Enable 403 status on login failed.
* Tags: security, login
* Version: 1.0
* License: MIT
* Author: Sean Walter
* Author URI: https://sitewrangler.org/
*
*/

add_action( 'wp_login_failed', function () {
    status_header(403);
} );

add_action( 'xmlrpc_login_error', function () {
    status_header(403);
} );

