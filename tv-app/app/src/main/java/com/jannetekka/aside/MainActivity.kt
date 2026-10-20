package com.jannetekka.aside

import android.annotation.SuppressLint
import android.app.Activity
import android.graphics.Color
import android.os.Bundle
import android.speech.tts.TextToSpeech
import android.view.KeyEvent
import android.view.View
import android.view.WindowManager
import android.webkit.JavascriptInterface
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import java.net.HttpURLConnection
import java.net.URL
import java.util.Locale
import kotlin.concurrent.thread

/**
 * Aside on Fire OS: a full-screen WebView running the Aside TV app, plus the parts a web page
 * can't do on its own: the Back, Menu and media keys of the Fire TV remote, and on-device speech
 * as a fallback for reading answers aloud.
 */
class MainActivity : Activity() {

    private lateinit var web: WebView
    private var tts: TextToSpeech? = null
    private var ttsReady = false
    private var base = BuildConfig.ASIDE_URL

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)

        web = WebView(this).apply {
            setBackgroundColor(Color.BLACK)
            isFocusable = true
            isFocusableInTouchMode = true
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.mediaPlaybackRequiresUserGesture = false
            settings.cacheMode = WebSettings.LOAD_DEFAULT
            settings.userAgentString = settings.userAgentString + " AsideFireTV/" + BuildConfig.VERSION_NAME
            addJavascriptInterface(Bridge(), "AsideNative")
            webViewClient = object : WebViewClient() {
                override fun onReceivedError(view: WebView, request: WebResourceRequest, error: WebResourceError) {
                    if (request.isForMainFrame) view.loadUrl("file:///android_asset/offline.html")
                }
            }
        }
        setContentView(web)
        web.requestFocus(View.FOCUS_DOWN)

        tts = TextToSpeech(this) { status ->
            ttsReady = status == TextToSpeech.SUCCESS
            if (ttsReady) tts?.language = Locale.US
        }
        start()
    }

    /** Find the service (tv-app/endpoint.txt in the repo, so it can move without a new APK), then load it. */
    private fun start() {
        web.loadUrl("file:///android_asset/loading.html")
        thread {
            val found = try {
                val c = URL(BuildConfig.ENDPOINT_URL).openConnection() as HttpURLConnection
                c.connectTimeout = 4000
                c.readTimeout = 4000
                c.inputStream.bufferedReader().readText().trim().takeIf { it.startsWith("https://") }
            } catch (e: Exception) {
                null
            }
            if (found != null) base = if (found.endsWith("/")) found else "$found/"
            runOnUiThread { web.loadUrl(base + "tv/") }
        }
    }

    private fun js(code: String, then: ((String) -> Unit)? = null) {
        web.evaluateJavascript(code) { then?.invoke(it ?: "") }
    }

    override fun dispatchKeyEvent(event: KeyEvent): Boolean {
        val name = when (event.keyCode) {
            KeyEvent.KEYCODE_MENU -> "menu"
            KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE, KeyEvent.KEYCODE_MEDIA_PLAY, KeyEvent.KEYCODE_MEDIA_PAUSE -> "playpause"
            KeyEvent.KEYCODE_MEDIA_REWIND -> "rewind"
            KeyEvent.KEYCODE_MEDIA_FAST_FORWARD -> "ff"
            KeyEvent.KEYCODE_BACK -> "back"
            else -> null
        } ?: return super.dispatchKeyEvent(event)

        if (event.action == KeyEvent.ACTION_DOWN && event.repeatCount == 0) {
            if (name == "back") {
                // The page closes its top layer and says whether it used the key; if not, leave the app.
                js("(window.asideBack && window.asideBack()) ? 'yes' : 'no'") { used ->
                    if (!used.contains("yes")) {
                        if (web.url?.startsWith("file:") == true && web.canGoBack()) web.goBack() else finish()
                    }
                }
            } else {
                js("window.asideKey && window.asideKey('$name')")
            }
        }
        return true
    }

    override fun onPause() {
        super.onPause()
        js("(function(){var v=document.getElementById('video'); if(v && !v.paused) v.pause();})()")
    }

    override fun onDestroy() {
        tts?.shutdown()
        web.destroy()
        super.onDestroy()
    }

    inner class Bridge {
        @JavascriptInterface
        fun speak(text: String) {
            if (ttsReady) tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, "aside")
        }

        @JavascriptInterface
        fun stop() {
            tts?.stop()
        }

        @JavascriptInterface
        fun retry() {
            runOnUiThread { start() }
        }

        @JavascriptInterface
        fun version(): String = BuildConfig.VERSION_NAME
    }
}
