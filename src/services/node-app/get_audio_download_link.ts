import VOTClient from "@vot.js/node";
import {getVideoData} from "@vot.js/node/utils/videoData";

async function main(args: string[]): Promise<void> {

//     const origLog = console.log;
//     console.log = (...args: any[]) => {
//         const stack = new Error().stack?.split("\n").slice(2).join("\n");
//         origLog("🔍 LOG CALL:", ...args);
//         origLog("  at", stack);
//     };

    type InputLang = "auto" | "ru" | "en" | "zh" | "ko" | "lt" | "lv" | "ar" | "fr" | "it" | "es" | "de" | "ja";
    type OutputLang = "ru" | "en" | "kk";

    const inputLang = args[0]! as InputLang;
    const outputLang = args[1]! as OutputLang;
    const url: string = args[2]!;

    const client = new VOTClient();

    const videoData = await getVideoData(url);
    let response = await client.translateVideo({
        videoData: videoData,
        requestLang: inputLang,
        responseLang: outputLang
    });

//     const subs = await client.getSubtitles({
//         videoData,
//         requestLang: "ru",
// });

    console.log(JSON.stringify(response, null, 2));
}

main(process.argv.slice(2)).catch((error) => {
    let code;
    let message = error.message;
    let data = error.data;
    if (error.message.includes("Yandex couldn't translate video")) {
        code = "SERVER_ERROR"
    } else {
        if (error.message.includes("Failed to request create session")) {
            code = "CLIENT_ERROR"
        } else {
            code = error.code
        }
    }
    if (error?.data) {
        data = error.data;
    }
    console.error(JSON.stringify({
        error: error,
        code,
        message,
        data
    }));

    process.exit(1);
});