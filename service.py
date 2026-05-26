from kivy.utils import platform
# Kivy Service script: Runs in a dedicated background JVM thread.
# NOTE: This file must NEVER import kivy.app, kivy.lang, kivy.uix or any UI module.
# Only kivy.utils.platform is used to guard the import block.
if platform != 'android':
    import sys
    sys.exit(0)

from os import environ
from time import sleep

# -----------------------------------------------------------------------
# GLOBAL REFERENCES
# These are kept at module level to prevent Python's GC from destroying
# JVM-linked objects (BroadcastReceiver / MediaSession) after the
# start_service() function exits.
# -----------------------------------------------------------------------
_receiver = None
_media_session = None


def start_service():
    global _receiver, _media_session

    from android import api_version  # type: ignore
    from jnius import autoclass, PythonJavaClass, java_method  # type: ignore

    print("[SERVICE] ===== start_service() called =====")
    print(f"[SERVICE] Running on API level: {api_version}")

    # ------------------------------------------------------------------
    # Core Android classes (no Kivy UI dependency)
    # ------------------------------------------------------------------
    PythonService      = autoclass('org.kivy.android.PythonService')
    service            = PythonService.mService

    Context            = autoclass('android.content.Context')
    Intent             = autoclass('android.content.Intent')
    PendingIntent      = autoclass('android.app.PendingIntent')
    NotificationManager = autoclass('android.app.NotificationManager')
    NotificationChannel = autoclass('android.app.NotificationChannel')
    NotificationBuilder = autoclass('android.app.Notification$Builder')
    NotificationAction  = autoclass('android.app.Notification$Action$Builder')
    MediaSession       = autoclass('android.media.session.MediaSession')
    MediaStyle         = autoclass('android.app.Notification$MediaStyle')

    # FIX 1: ICON – Use the app's own launcher icon via mipmap resources.
    # R.drawable.ic_media_play often doesn't exist in packaged apps and
    # silently causes the entire notification to be rejected by Android.
    Resources = service.getResources()
    pkg       = service.getPackageName()
    icon_res  = Resources.getIdentifier('icon', 'mipmap', pkg)
    if icon_res == 0:
        # Fallback to the generic Android play icon if mipmap/icon is missing
        R_drawable = autoclass('android.R$drawable')
        icon_res   = R_drawable.ic_media_play
        print(f"[SERVICE] WARNING: mipmap/icon not found, using fallback ic_media_play")
    else:
        print(f"[SERVICE] Icon resource id = {icon_res}  (mipmap/icon)")

    # ------------------------------------------------------------------
    # FIX 2: CHANNEL ID – Rotated to force Android / MIUI to create a
    # brand-new channel with IMPORTANCE_MAX so lock-screen heads-up is
    # never suppressed by a cached low-importance channel entry.
    # ------------------------------------------------------------------
    channel_id = 'notif_audio_v4_fix'
    nm         = service.getSystemService(Context.NOTIFICATION_SERVICE)

    if api_version >= 26:
        print(f"[SERVICE] Creating notification channel: {channel_id}")
        channel = NotificationChannel(
            channel_id,
            'Reproductor Multimedia',
            NotificationManager.IMPORTANCE_MAX   # = 5, highest possible
        )
        channel.setDescription('Controles de reproducción de música')
        channel.setShowBadge(True)
        # Allow the channel to appear on the lock screen at full detail
        channel.setLockscreenVisibility(1)  # VISIBILITY_PUBLIC = 1
        nm.createNotificationChannel(channel)
        print(f"[SERVICE] Channel '{channel_id}' registered with IMPORTANCE_MAX")

    # ------------------------------------------------------------------
    # PendingIntent flags (mandatory from Android 12 / API 31)
    # FLAG_UPDATE_CURRENT = 0x08000000
    # FLAG_IMMUTABLE      = 0x04000000
    # ------------------------------------------------------------------
    FLAG_UPDATE_CURRENT = 0x08000000
    FLAG_IMMUTABLE      = 0x04000000
    pi_flags            = FLAG_UPDATE_CURRENT | FLAG_IMMUTABLE

    def make_pi(action_name, request_code):
        intent = Intent(action_name)
        return PendingIntent.getBroadcast(service, request_code, intent, pi_flags)

    pi_play  = make_pi("org.test.musicplayeryt.ACTION_PLAY",  1)
    pi_pause = make_pi("org.test.musicplayeryt.ACTION_PAUSE", 2)
    pi_next  = make_pi("org.test.musicplayeryt.ACTION_NEXT",  3)
    pi_prev  = make_pi("org.test.musicplayeryt.ACTION_PREV",  4)

    print("[SERVICE] PendingIntents created with FLAG_IMMUTABLE")

    # ------------------------------------------------------------------
    # MediaSession – global reference prevents GC destruction
    # ------------------------------------------------------------------
    _media_session = MediaSession(service, "KivyMediaSession")
    _media_session.setActive(True)

    # PlaybackState (MANDATORY for Android 13+ lock-screen widget)
    # Actions mask 54 = PLAY(4) | PAUSE(2) | SKIP_NEXT(32) | SKIP_PREV(16)
    PlaybackStateBuilder = autoclass('android.media.session.PlaybackState$Builder')
    psb = PlaybackStateBuilder()
    psb.setActions(54)
    psb.setState(3, 0, 1.0)  # STATE_PLAYING = 3
    _media_session.setPlaybackState(psb.build())

    print("[SERVICE] MediaSession created and set to STATE_PLAYING")

    # ------------------------------------------------------------------
    # build_notification() – pure function, no Kivy UI dependency
    # ------------------------------------------------------------------
    def build_notification(title='Reproductor Activo', artist='Escuchando música...', state='playing'):
        """Returns a fresh MediaStyle Notification object."""
        fresh_style = MediaStyle()
        fresh_style.setMediaSession(_media_session.getSessionToken())
        fresh_style.setShowActionsInCompactView(0, 1, 2)

        if api_version >= 26:
            b = NotificationBuilder(service, channel_id)
        else:
            b = NotificationBuilder(service)

        b.setContentTitle(title)
        b.setContentText(artist)
        b.setSmallIcon(icon_res)      # FIX 1: mipmap resource id, not R.drawable
        b.setVisibility(1)            # VISIBILITY_PUBLIC
        b.setOngoing(True)

        b.addAction(NotificationAction(icon_res, "Prev", pi_prev).build())

        if state == 'playing':
            b.addAction(NotificationAction(icon_res, "Pause", pi_pause).build())
        else:
            b.addAction(NotificationAction(icon_res, "Play",  pi_play).build())

        b.addAction(NotificationAction(icon_res, "Next", pi_next).build())
        b.setStyle(fresh_style)
        return b.build()

    # ------------------------------------------------------------------
    # FIX 4: INSTRUMENTED startForeground() CALL
    # These prints will appear in `adb logcat | grep SERVICE` so you can
    # confirm exactly where execution reaches or stops.
    # ------------------------------------------------------------------
    print("[SERVICE] Building initial notification …")
    notification = build_notification()
    print("[SERVICE] Notification object built OK")

    print(f"[SERVICE] Calling startForeground(1, notification, type=2) …  api={api_version}")
    try:
        if api_version >= 29:
            # type 2 = FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK
            service.startForeground(1, notification, 2)
        else:
            service.startForeground(1, notification)
        print("[SERVICE] startForeground() completed successfully ✓")
    except Exception as sf_err:
        print(f"[SERVICE] ERROR in startForeground(): {sf_err}")
        raise

    # ------------------------------------------------------------------
    # BroadcastReceiver – module-level global prevents GC destruction
    # FIX 3: No Kivy UI imports inside this class (only jnius + android)
    # ------------------------------------------------------------------
    class MetadataReceiver(PythonJavaClass):
        __javainterfaces__ = ['android/content/BroadcastReceiver']
        __javacontext__    = 'app'

        @java_method('(Landroid/content/Context;Landroid/content/Intent;)V')
        def onReceive(self, context, intent):
            try:
                action = intent.getAction()
                print(f"[SERVICE] onReceive: {action}")

                if action == "org.test.musicplayeryt.UPDATE_METADATA":
                    title  = intent.getStringExtra("title")  or "Reproductor Activo"
                    artist = intent.getStringExtra("artist") or "Escuchando música..."
                    state  = intent.getStringExtra("state")  or "playing"

                    # Rebuild and post the updated notification
                    nm.notify(1, build_notification(title, artist, state))
                    print(f"[SERVICE] Notification updated – title={title!r}  state={state!r}")

                    # Update PlaybackState for lock-screen widget
                    try:
                        ps_builder = autoclass('android.media.session.PlaybackState$Builder')()
                        ps_builder.setActions(54)
                        state_int = 3 if state == 'playing' else 2  # PLAYING=3, PAUSED=2
                        ps_builder.setState(state_int, 0, 1.0)
                        _media_session.setPlaybackState(ps_builder.build())
                    except Exception as ps_e:
                        print(f"[SERVICE] PlaybackState update error: {ps_e}")

                    # Update MediaSession metadata (title/artist on lock screen)
                    try:
                        MediaMetadataBuilder = autoclass('android.media.MediaMetadata$Builder')
                        meta = MediaMetadataBuilder()
                        meta.putString('android.media.metadata.TITLE',  title)
                        meta.putString('android.media.metadata.ARTIST', artist)
                        _media_session.setMetadata(meta.build())
                    except Exception as meta_e:
                        print(f"[SERVICE] MediaMetadata error: {meta_e}")

            except Exception as e:
                print(f"[SERVICE] Receiver exception: {e}")

    _receiver   = MetadataReceiver()
    IntentFilter = autoclass('android.content.IntentFilter')
    ifilter      = IntentFilter("org.test.musicplayeryt.UPDATE_METADATA")

    if api_version >= 33:
        service.registerReceiver(_receiver, ifilter, 2)  # RECEIVER_EXPORTED = 2
    else:
        service.registerReceiver(_receiver, ifilter)

    print("[SERVICE] MetadataReceiver registered. Entering keep-alive loop.")

    # Keep the service thread alive
    while True:
        sleep(5)


if __name__ == '__main__':
    try:
        start_service()
    except Exception as e:
        print(f"[SERVICE] CRITICAL EXCEPTION: {e}")
        while True:
            sleep(10)
