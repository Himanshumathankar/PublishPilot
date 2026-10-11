<?php
/**
 * Plugin Name: TWPublisher Connector
 * Description: Securely connects TWPublisher to WordPress for author discovery and Rank Math SEO metadata publishing.
 * Version: 2.0.1
 * Requires at least: 6.0
 * Requires PHP: 7.4
 * Author: Takeweb
 * License: GPL-2.0-or-later
 * License URI: https://www.gnu.org/licenses/gpl-2.0.html
 * Text Domain: twpublisher-connector
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

define( 'TWPUBLISHER_CONNECTOR_VERSION', '2.0.1' );
define( 'TWPUBLISHER_CONNECTOR_FILE', __FILE__ );
define( 'TWPUBLISHER_CONNECTOR_PATH', plugin_dir_path( __FILE__ ) );

require_once TWPUBLISHER_CONNECTOR_PATH . 'includes/class-rest-controller.php';
require_once TWPUBLISHER_CONNECTOR_PATH . 'includes/class-plugin.php';

TWPublisher\Connector\Plugin::instance()->boot();
