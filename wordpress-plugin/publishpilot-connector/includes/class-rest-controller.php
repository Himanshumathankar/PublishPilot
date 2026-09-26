<?php
/**
 * Rank Math REST endpoint.
 *
 * @package PublishPilotConnector
 */

namespace PublishPilot\Connector;

use WP_Error;
use WP_REST_Request;
use WP_REST_Response;
use WP_REST_Server;

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/** Handles authenticated Rank Math metadata updates. */
final class Rest_Controller {
	const NAMESPACE = 'publishpilot/v1';
	const LEGACY_NAMESPACE = 'article-publisher/v1';
	const ROUTE = '/rank-math';
	const AUTHORS_ROUTE = '/authors';

	/** Register the private endpoint. */
	public function register_routes() {
		register_rest_route(
			self::NAMESPACE,
			self::ROUTE,
			array(
				'methods'             => WP_REST_Server::CREATABLE,
				'permission_callback' => array( $this, 'permissions_check' ),
				'callback'            => array( $this, 'update_metadata' ),
				'args'                => $this->get_endpoint_args(),
			)
		);
		register_rest_route(
			self::LEGACY_NAMESPACE,
			self::ROUTE,
			array(
				'methods'             => WP_REST_Server::CREATABLE,
				'permission_callback' => array( $this, 'permissions_check' ),
				'callback'            => array( $this, 'update_metadata' ),
				'args'                => $this->get_endpoint_args(),
			)
		);
		register_rest_route(
			self::NAMESPACE,
			self::AUTHORS_ROUTE,
			array(
				'methods'             => WP_REST_Server::READABLE,
				'permission_callback' => array( $this, 'authors_permissions_check' ),
				'callback'            => array( $this, 'get_authors' ),
			)
		);
		register_rest_route(
			self::LEGACY_NAMESPACE,
			self::AUTHORS_ROUTE,
			array(
				'methods'             => WP_REST_Server::READABLE,
				'permission_callback' => array( $this, 'authors_permissions_check' ),
				'callback'            => array( $this, 'get_authors' ),
			)
		);
	}

	/** Only users who can assign another post author may list eligible authors. */
	public function authors_permissions_check() {
		if ( ! current_user_can( 'edit_others_posts' ) ) {
			return new WP_Error(
				'publishpilot_authors_forbidden',
				__( 'You are not allowed to assign other post authors.', 'publishpilot-connector' ),
				array( 'status' => rest_authorization_required_code() )
			);
		}
		return true;
	}

	/** Return only WordPress users eligible to author standard posts. */
	public function get_authors() {
		$query = new \WP_User_Query(
			array(
				'capability' => 'edit_posts',
				'orderby' => 'display_name',
				'order'   => 'ASC',
				'fields'  => array( 'ID', 'display_name', 'user_login' ),
			)
		);
		$authors = array_map(
			static function ( $user ) {
				return array(
					'id'       => (int) $user->ID,
					'name'     => $user->display_name,
					'username' => $user->user_login,
				);
			},
			$query->get_results()
		);
		return new WP_REST_Response( $authors, 200 );
	}

	/** Return the endpoint argument schema. */
	private function get_endpoint_args() {
		return array(
			'post_id'     => array(
				'required'          => true,
				'type'              => 'integer',
				'minimum'           => 1,
				'sanitize_callback' => 'absint',
			),
			'title'       => array(
				'required'          => true,
				'type'              => 'string',
				'validate_callback' => array( $this, 'validate_text' ),
				'sanitize_callback' => 'sanitize_text_field',
			),
			'description' => array(
				'required'          => true,
				'type'              => 'string',
				'validate_callback' => array( $this, 'validate_text' ),
				'sanitize_callback' => 'sanitize_textarea_field',
			),
		);
	}

	/** Validate bounded strings without silently truncating them. */
	public function validate_text( $value, WP_REST_Request $request, $key ) {
		unset( $request );
		$maximum = 'title' === $key ? 2048 : 10000;
		return is_string( $value ) && '' !== trim( $value ) && strlen( $value ) <= $maximum;
	}

	/** Allow updates only for users who can edit the requested standard post. */
	public function permissions_check( WP_REST_Request $request ) {
		$post_id = absint( $request->get_param( 'post_id' ) );
		$post = get_post( $post_id );

		if ( ! $post || 'post' !== $post->post_type ) {
			return new WP_Error(
				'publishpilot_invalid_post',
				__( 'A valid WordPress post is required.', 'publishpilot-connector' ),
				array( 'status' => 404 )
			);
		}

		if ( ! current_user_can( 'edit_post', $post_id ) ) {
			return new WP_Error(
				'publishpilot_forbidden',
				__( 'You are not allowed to update this post.', 'publishpilot-connector' ),
				array( 'status' => rest_authorization_required_code() )
			);
		}

		return true;
	}

	/** Store and verify the two supported Rank Math fields. */
	public function update_metadata( WP_REST_Request $request ) {
		$post_id = absint( $request->get_param( 'post_id' ) );
		$title = sanitize_text_field( $request->get_param( 'title' ) );
		$description = sanitize_textarea_field( $request->get_param( 'description' ) );

		update_post_meta( $post_id, 'rank_math_title', $title );
		update_post_meta( $post_id, 'rank_math_description', $description );

		$verified = get_post_meta( $post_id, 'rank_math_title', true ) === $title
			&& get_post_meta( $post_id, 'rank_math_description', true ) === $description;

		if ( ! $verified ) {
			return new WP_Error(
				'publishpilot_rank_math_update_failed',
				__( 'Rank Math metadata could not be verified.', 'publishpilot-connector' ),
				array( 'status' => 500 )
			);
		}

		return new WP_REST_Response( array( 'success' => true ), 200 );
	}
}
