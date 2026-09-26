<?php
/**
 * Plugin Name: PublishPilot Connector
 * Description: Securely connects PublishPilot to WordPress for author discovery and Rank Math SEO metadata publishing.
 * Version: 2.0.0
 * Requires at least: 6.0
 * Requires PHP: 7.4
 * Author: PublishPilot
 * License: GPL-2.0-or-later
 * License URI: https://www.gnu.org/licenses/gpl-2.0.html
 * Text Domain: publishpilot-connector
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

define( 'PUBLISHPILOT_CONNECTOR_VERSION', '2.0.0' );
define( 'PUBLISHPILOT_CONNECTOR_FILE', __FILE__ );
define( 'PUBLISHPILOT_CONNECTOR_PATH', plugin_dir_path( __FILE__ ) );

require_once PUBLISHPILOT_CONNECTOR_PATH . 'includes/class-rest-controller.php';
require_once PUBLISHPILOT_CONNECTOR_PATH . 'includes/class-plugin.php';

PublishPilot\Connector\Plugin::instance()->boot();
