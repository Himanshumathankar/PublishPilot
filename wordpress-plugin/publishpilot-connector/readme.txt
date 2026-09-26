=== PublishPilot Connector ===
Contributors: himanshumathankar
Tags: publishing, editorial, rank-math, rest-api, multisite
Requires at least: 6.0
Tested up to: 6.8
Requires PHP: 7.4
Stable tag: 2.0.0
License: GPLv2 or later
License URI: https://www.gnu.org/licenses/gpl-2.0.html

Securely connects the PublishPilot editorial application to WordPress for author discovery and Rank Math SEO metadata publishing.

== Description ==

PublishPilot Connector is the WordPress-side integration for PublishPilot, an editorial workflow application used to review and publish articles across multiple WordPress websites.

The plugin provides two authenticated REST API capabilities:

* Lists users who have the `edit_posts` capability so PublishPilot can present an accurate author selector, including sites with custom roles.
* Writes and verifies the Rank Math SEO title and meta description for a specific standard WordPress post.

The plugin does not create posts, upload media, collect analytics, display advertising, add front-end branding, or modify WordPress core. Post creation and media uploads use the standard WordPress REST API.

== Security ==

Every endpoint requires an authenticated WordPress user. Application Passwords are supported through WordPress core.

* Author discovery requires the `edit_others_posts` capability and returns only the user ID, display name, and username of accounts that can edit posts.
* SEO updates require `edit_post` permission for the requested post.
* Only standard `post` records are accepted for SEO updates.
* Input is type checked, length limited, sanitized, stored, and verified before success is returned.
* Direct file access is blocked.

Use a dedicated WordPress account with only the permissions required by your publishing workflow. Revoke its Application Password immediately if it is exposed.

== Privacy and external services ==

This plugin does not collect telemetry, set cookies, track visitors, or contact third-party servers. It only responds to authenticated requests received by the WordPress REST API.

When a site administrator intentionally connects the separate PublishPilot application, that application sends publishing data to this WordPress website. The plugin itself does not transmit WordPress data to PublishPilot or any other external service.

Rank Math is not bundled with this plugin. If Rank Math is installed, PublishPilot Connector updates two Rank Math post-meta fields requested by the authenticated publishing client.

== Installation ==

1. If the former Article Publisher Rank Math Bridge is installed, deactivate and delete that plugin first. Its settings are not stored in WordPress, so no site data is removed.
2. Upload the `publishpilot-connector` folder to `/wp-content/plugins/`, or install the ZIP from Plugins > Add New > Upload Plugin.
3. Activate PublishPilot Connector.
4. In WordPress, create an Application Password for the account PublishPilot will use.
5. In PublishPilot Settings, add the website URL, username, and Application Password.
6. Use `/wp-json/publishpilot/v1/rank-math` as the Rank Math endpoint.

== Frequently Asked Questions ==

= Does this plugin publish posts? =

PublishPilot publishes posts through the standard WordPress REST API. This connector handles author discovery and Rank Math metadata only.

= Why is the author endpoint needed? =

WordPress installations with custom roles can allow users to author posts while excluding them from the core REST API's legacy author filter. The connector checks the actual `edit_posts` capability.

= Does it expose the WordPress user database? =

No. The endpoint requires authentication and `edit_others_posts`. It returns only IDs, display names, and usernames for users capable of editing posts. It does not return email addresses, passwords, or profile metadata.

= Does it send data to an external service? =

No. The plugin does not initiate external requests. It responds only when an authenticated client calls its REST endpoints.

= Are old Article Publisher endpoints supported? =

Yes. Version 2.0 retains the previous endpoint namespace as a compatibility alias so existing configured sites keep working during migration.

= Does the plugin support automatic updates? =

WordPress can provide standard automatic updates after PublishPilot Connector is approved and hosted in the WordPress.org Plugin Directory. The plugin intentionally does not install updates from a custom server.

== REST API ==

`GET /wp-json/publishpilot/v1/authors`

Returns eligible post authors. Requires `edit_others_posts`.

`POST /wp-json/publishpilot/v1/rank-math`

Accepts `post_id`, `title`, and `description`. Requires permission to edit the specified post.

== Upgrade Notice ==

= 2.0.0 =

Rebranded as PublishPilot Connector. Existing endpoint URLs remain supported for compatibility.

== Changelog ==

= 2.0.0 =
* Renamed the plugin to PublishPilot Connector.
* Added the PublishPilot REST namespace while retaining legacy routes.
* Expanded security, privacy, installation, and usage documentation.
* Detects eligible authors using the `edit_posts` capability for custom-role compatibility.
* Returns current WordPress display names and usernames.

= 1.3.1 =
* Added current WordPress usernames alongside author display names.

= 1.3.0 =
* Added a capability-protected list of users eligible to author posts.

= 1.2.0 =
* Reorganized the plugin into a conventional bootstrap and class structure.
* Retained capability checks, post-type restrictions, validation, and verification.

= 1.1.0 =
* Added strict input validation and post-level authorization.

= 1.0.0 =
* Initial release.
