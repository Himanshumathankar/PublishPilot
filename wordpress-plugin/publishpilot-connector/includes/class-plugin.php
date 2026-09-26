<?php
/**
 * Main plugin coordinator.
 *
 * @package PublishPilotConnector
 */

namespace PublishPilot\Connector;

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/** Coordinates plugin hooks. */
final class Plugin {
	/** @var self|null */
	private static $instance = null;

	/** @var Rest_Controller */
	private $rest_controller;

	/** Return the single plugin instance. */
	public static function instance() {
		if ( null === self::$instance ) {
			self::$instance = new self();
		}
		return self::$instance;
	}

	/** Register WordPress hooks. */
	public function boot() {
		$this->rest_controller = new Rest_Controller();
		add_action( 'rest_api_init', array( $this->rest_controller, 'register_routes' ) );
	}

	/** Prevent direct construction. */
	private function __construct() {}

	/** Prevent cloning. */
	private function __clone() {}
}
