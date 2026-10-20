import {WebView} from '@amazon-devices/webview';
import * as React from 'react';
import {useRef, useState} from 'react';
import {BackHandler, Pressable, StyleSheet, Text, View} from 'react-native';
import {
  useHideSplashScreenCallback,
  usePreventHideSplashScreen,
} from '@amazon-devices/react-native-kepler';
import {
  WebViewErrorEvent,
  WebViewMessageEvent,
  WebViewNavigationEvent,
} from '@amazon-devices/webview/dist/types/WebViewTypes';

// Aside on Vega OS: a full-screen WebView running the Aside TV app from the server.
// The page handles the remote itself (D-pad, Select, media keys, and Back as keyCode 27
// "GoBack" thanks to allowSystemKeyEvents). At its home screen it posts EXIT_APP and we leave.
const ASIDE_URL = 'https://aside-tv.onrender.com/tv/';

export const App = () => {
  const webRef = useRef<WebView>(null);
  const [failed, setFailed] = useState(false);
  usePreventHideSplashScreen();
  const hideSplashScreen = useHideSplashScreenCallback();

  const onMessage = (event: WebViewMessageEvent) => {
    if (event.nativeEvent.data === 'EXIT_APP') {
      BackHandler.exitApp();
    }
  };

  return (
    <View style={styles.container}>
      <WebView
        ref={webRef}
        style={styles.webview}
        source={{uri: ASIDE_URL}}
        allowSystemKeyEvents
        allowsDefaultMediaControl={false}
        domStorageEnabled
        hasTVPreferredFocus
        javaScriptEnabled
        mediaPlaybackRequiresUserAction={false}
        onMessage={onMessage}
        onCloseWindow={() => BackHandler.exitApp()}
        onLoad={(_event: WebViewNavigationEvent) => {
          setFailed(false);
          hideSplashScreen();
        }}
        onError={({nativeEvent: {code, url, description}}: WebViewErrorEvent) => {
          console.error(`[Aside] load error ${code} ${url}: ${description}`);
          setFailed(true);
          hideSplashScreen();
        }}
      />
      {failed && (
        <View style={styles.offline}>
          <Text style={styles.title}>Aside can't reach its service</Text>
          <Text style={styles.body}>
            Check that the Fire TV is online. If the server was asleep, it can take up to a minute to wake up.
          </Text>
          <Pressable
            hasTVPreferredFocus
            style={({focused}) => [styles.button, focused && styles.buttonFocused]}
            onPress={() => {
              setFailed(false);
              webRef.current?.reload();
            }}>
            <Text style={styles.buttonText}>Try again</Text>
          </Pressable>
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: '#0b0c10'},
  webview: {backgroundColor: '#0b0c10'},
  offline: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: '#0b0c10',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 80,
  },
  title: {color: '#f4f1ea', fontSize: 44, fontWeight: '600', marginBottom: 20},
  body: {color: '#b3ada2', fontSize: 28, textAlign: 'center', maxWidth: 1100, marginBottom: 40},
  button: {paddingHorizontal: 48, paddingVertical: 20, borderRadius: 40, backgroundColor: '#22252e'},
  buttonFocused: {backgroundColor: '#ffffff'},
  buttonText: {color: '#f2b544', fontSize: 30, fontWeight: '600'},
});
