extends Node
## Autoload "Services": external services behind interfaces.
## Each one degrades gracefully: no network, no native plugin -> the game still runs.

var config: RemoteConfigService
var analytics: AnalyticsService
var crash: CrashReporter
var backend: BackendClient
var debug_analytics: DebugAnalyticsProvider

var _analytics_bridge: AnalyticsEventBridge


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	config = RemoteConfigService.new(Content.config)
	config.load_cached()

	crash = CrashReporter.new()
	crash.enabled = config.is_feature_enabled("crash_reporting_enabled")
	crash.set_custom_key("game_version", config.game_version())
	crash.set_custom_key("content_version", str(Content.content_version))
	OS.add_logger(CrashLogger.new(crash))

	analytics = AnalyticsService.new()
	analytics.enabled = config.is_feature_enabled("analytics_enabled")
	analytics.set_context("game_version", config.game_version())
	analytics.set_context("content_version", Content.content_version)
	analytics.set_context("platform", OS.get_name())
	debug_analytics = DebugAnalyticsProvider.new()
	analytics.add_provider(debug_analytics)
	analytics.add_provider(FirebaseAnalyticsProvider.new())
	_analytics_bridge = AnalyticsEventBridge.new(analytics)

	backend = BackendClient.new()
