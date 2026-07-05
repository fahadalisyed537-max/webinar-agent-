import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
    appId: 'com.mindbloom.wellness',
    appName: 'MindBloom',
    webDir: 'www',
    server: {
        androidScheme: 'https'
    },
    android: {
        allowMixedContent: false,
        captureInput: true,
        webContentsDebuggingEnabled: false
    },
    plugins: {
        SplashScreen: {
            launchShowDuration: 2000,
            launchAutoHide: true,
            backgroundColor: '#0f0f1a',
            androidSplashResourceName: 'splash',
            androidScaleType: 'CENTER_CROP',
            showSpinner: false
        },
        StatusBar: {
            style: 'DARK',
            backgroundColor: '#0f0f1a'
        }
    }
};

export default config;
