import type { PhraseItem } from "./types";

export interface ScriptStep {
  /** What the tutor says in Cantonese. */
  tutor: PhraseItem;
  /** English hint of what the learner should try to say. */
  hint: string;
  /** Lowercase English keywords that indicate the learner's intent matches. */
  acceptKeywords: string[];
  /** Phrase taught when the learner speaks English at this step. */
  teach: PhraseItem;
}

export interface LikelyMistake {
  mistake: string;
  correction: string;
  explanation: string;
}

export interface Scenario {
  id: string;
  title: string;
  subtitle: string;
  icon: string;
  color: string;
  minutes: number;
  setting: string;
  objectives: string[];
  targetPhrases: PhraseItem[];
  openingLine: PhraseItem;
  script: ScriptStep[];
  likelyMistakes: LikelyMistake[];
  assessmentPhrases: PhraseItem[];
}

export const SCENARIOS: Scenario[] = [
  {
    id: "greetings",
    title: "Greetings & Introductions",
    subtitle: "Say hello, introduce yourself, small talk",
    icon: "👋",
    color: "from-amber-500/20 to-orange-500/10",
    minutes: 5,
    setting: "Meeting a neighbour in your building lobby in Hong Kong.",
    objectives: [
      "Greet appropriately by time of day",
      "Introduce your name and where you are from",
      "Ask how someone is doing and respond",
      "Use polite particles (唔該 / 多謝) correctly",
    ],
    targetPhrases: [
      { cantonese: "早晨！", jyutping: "zou2 san4!", english: "Good morning!", note: "Used before noon; more common than 你好 in daily life." },
      { cantonese: "你好，我叫 Alex。", jyutping: "nei5 hou2, ngo5 giu3 Alex.", english: "Hello, my name is Alex." },
      { cantonese: "我係美國人。", jyutping: "ngo5 hai6 mei5 gwok3 jan4.", english: "I am American.", note: "Swap 美國 for your country: 英國 jing1 gwok3, 澳洲 ou3 zau1…" },
      { cantonese: "你近排點呀？", jyutping: "nei5 gan6 paai4 dim2 aa3?", english: "How have you been lately?" },
      { cantonese: "幾好呀，多謝！", jyutping: "gei2 hou2 aa3, do1 ze6!", english: "Pretty good, thanks!", note: "多謝 do1 ze6 thanks gifts/favours; 唔該 m4 goi1 thanks services." },
      { cantonese: "好高興認識你。", jyutping: "hou2 gou1 hing3 jing6 sik1 nei5.", english: "Nice to meet you." },
      { cantonese: "你識唔識講英文？", jyutping: "nei5 sik1 m4 sik1 gong2 jing1 man2?", english: "Can you speak English?" },
      { cantonese: "遲啲見，拜拜！", jyutping: "ci4 di1 gin3, baai1 baai3!", english: "See you later, bye!" },
    ],
    openingLine: { cantonese: "早晨！我係陳太，你係新搬嚟嘅？", jyutping: "zou2 san4! ngo5 hai6 can4 taai3, nei5 hai6 san1 bun1 lai4 ge3?", english: "Good morning! I'm Mrs Chan — did you just move in?" },
    script: [
      {
        tutor: { cantonese: "早晨！你係咪新搬嚟嘅？", jyutping: "zou2 san4! nei5 hai6 mai6 san1 bun1 lai4 ge3?", english: "Good morning! Are you new here?" },
        hint: "Greet her back and say yes, you just moved in.",
        acceptKeywords: ["morning", "yes", "moved", "new", "你好", "早晨", "係"],
        teach: { cantonese: "早晨！係呀，我啱啱搬入嚟。", jyutping: "zou2 san4! hai6 aa3, ngo5 ngaam5 ngaam1 bun1 jap6 lai4.", english: "Good morning! Yes, I just moved in." },
      },
      {
        tutor: { cantonese: "歡迎！你叫咩名呀？", jyutping: "fun1 jing4! nei5 giu3 me1 meng2 aa3?", english: "Welcome! What's your name?" },
        hint: "Tell her your name.",
        acceptKeywords: ["name", "called", "叫"],
        teach: { cantonese: "我叫 Alex。", jyutping: "ngo5 giu3 Alex.", english: "My name is Alex." },
      },
      {
        tutor: { cantonese: "你係邊度人呀？", jyutping: "nei5 hai6 bin1 dou6 jan4 aa3?", english: "Where are you from?" },
        hint: "Say which country you are from.",
        acceptKeywords: ["from", "america", "britain", "australia", "canada", "人"],
        teach: { cantonese: "我係美國人。", jyutping: "ngo5 hai6 mei5 gwok3 jan4.", english: "I'm American." },
      },
      {
        tutor: { cantonese: "哦！你廣東話講得幾好喎。住得慣唔慣呀？", jyutping: "o3! nei5 gwong2 dung1 waa2 gong2 dak1 gei2 hou2 wo3. zyu6 dak1 gwaan3 m4 gwaan3 aa3?", english: "Oh! Your Cantonese is pretty good. Are you used to living here?" },
        hint: "Thank her and say you are still learning / settling in.",
        acceptKeywords: ["thank", "learning", "still", "good", "多謝", "學"],
        teach: { cantonese: "多謝！我仲學緊，住得幾慣。", jyutping: "do1 ze6! ngo5 zung6 hok6 gan2, zyu6 dak1 gei2 gwaan3.", english: "Thanks! I'm still learning, and I'm settling in well." },
      },
      {
        tutor: { cantonese: "有咩需要就搵我啦。", jyutping: "jau5 me1 seoi1 jiu3 zau6 wan2 ngo5 laa1.", english: "If you need anything, come find me." },
        hint: "Thank her and say goodbye.",
        acceptKeywords: ["thank", "bye", "see you", "多謝", "拜拜"],
        teach: { cantonese: "好多謝你！遲啲見！", jyutping: "hou2 do1 ze6 nei5! ci4 di1 gin3!", english: "Thank you so much! See you later!" },
      },
    ],
    likelyMistakes: [
      { mistake: "多謝 for everything", correction: "唔該 vs 多謝", explanation: "Use 唔該 m4 goi1 for services (someone holding a door, a waiter), 多謝 do1 ze6 for gifts and compliments." },
      { mistake: "我是美國人 (Mandarin pattern)", correction: "我係美國人", explanation: "Cantonese uses 係 hai6, not 是 si6." },
      { mistake: "你叫什麼名字？", correction: "你叫咩名呀？", explanation: "咩名 me1 meng2 is the natural spoken form; 什麼名字 sounds like written Chinese." },
    ],
    assessmentPhrases: [
      { cantonese: "早晨！我叫 Alex，我係美國人。", jyutping: "zou2 san4! ngo5 giu3 Alex, ngo5 hai6 mei5 gwok3 jan4.", english: "Good morning! I'm Alex, I'm American." },
      { cantonese: "你近排點呀？", jyutping: "nei5 gan6 paai4 dim2 aa3?", english: "How have you been?" },
      { cantonese: "好高興認識你，遲啲見！", jyutping: "hou2 gou1 hing3 jing6 sik1 nei5, ci4 di1 gin3!", english: "Nice to meet you, see you later!" },
    ],
  },
  {
    id: "cha-chaan-teng",
    title: "Ordering at a Cha Chaan Teng",
    subtitle: "Milk tea, ordering, asking for the bill",
    icon: "🧋",
    color: "from-teal-500/20 to-emerald-500/10",
    minutes: 6,
    setting: "A bustling cha chaan teng (Hong Kong café) at lunch time.",
    objectives: [
      "Call the waiter politely with 唔該",
      "Order drinks with modifications (少甜, 走冰)",
      "Order food and takeaway",
      "Ask for the bill and price",
    ],
    targetPhrases: [
      { cantonese: "唔該，我要一杯凍奶茶。", jyutping: "m4 goi1, ngo5 jiu3 jat1 bui1 dung3 naai5 caa4.", english: "Excuse me, I'd like an iced milk tea." },
      { cantonese: "少甜，唔該。", jyutping: "siu2 tim4, m4 goi1.", english: "Less sweet, please." },
      { cantonese: "走冰。", jyutping: "zau2 bing1.", english: "No ice.", note: "走 zau2 = 'without' when ordering." },
      { cantonese: "我要一個菠蘿油。", jyutping: "ngo5 jiu3 jat1 go3 bo1 lo4 jau4.", english: "I'll have a pineapple bun with butter." },
      { cantonese: "堂食，唔該。", jyutping: "tong4 sik6, m4 goi1.", english: "For here, please.", note: "外賣 ngoi6 maai6 = takeaway." },
      { cantonese: "可唔可以快啲呀？", jyutping: "ho2 m4 ho2 ji5 faai3 di1 aa3?", english: "Could it be quicker?" },
      { cantonese: "埋單，唔該。", jyutping: "maai4 daan1, m4 goi1.", english: "The bill, please." },
      { cantonese: "幾多錢呀？", jyutping: "gei2 do1 cin2 aa3?", english: "How much is it?" },
    ],
    openingLine: { cantonese: "喂，老友，坐低先！飲咩呀？", jyutping: "wai3, lou5 jau5, co5 dai1 sin1! jam2 me1 aa3?", english: "Hey, friend, take a seat! What are you drinking?" },
    script: [
      {
        tutor: { cantonese: "飲咩呀？凍定熱？", jyutping: "jam2 me1 aa3? dung3 ding6 jit6?", english: "What'll you drink? Cold or hot?" },
        hint: "Order an iced milk tea, less sweet.",
        acceptKeywords: ["milk tea", "iced", "奶茶"],
        teach: { cantonese: "我要一杯凍奶茶，少甜。", jyutping: "ngo5 jiu3 jat1 bui1 dung3 naai5 caa4, siu2 tim4.", english: "I'd like an iced milk tea, less sweet." },
      },
      {
        tutor: { cantonese: "好！食唔食嘢呀？菠蘿油好新鮮嘅。", jyutping: "hou2! sik6 m4 sik6 je5 aa3? bo1 lo4 jau4 hou2 san1 sin1 ge3.", english: "OK! Want food? The pineapple buns are fresh." },
        hint: "Order a pineapple bun.",
        acceptKeywords: ["pineapple", "bun", "菠蘿", "yes"],
        teach: { cantonese: "好呀，我要一個菠蘿油。", jyutping: "hou2 aa3, ngo5 jiu3 jat1 go3 bo1 lo4 jau4.", english: "Sure, I'll have a pineapple bun with butter." },
      },
      {
        tutor: { cantonese: "堂食定外賣？", jyutping: "tong4 sik6 ding6 ngoi6 maai6?", english: "For here or to go?" },
        hint: "Say it's for here.",
        acceptKeywords: ["here", "eat in", "堂食"],
        teach: { cantonese: "堂食，唔該。", jyutping: "tong4 sik6, m4 goi1.", english: "For here, please." },
      },
      {
        tutor: { cantonese: "好，等一陣就嚟！", jyutping: "hou2, dang2 jat1 zan6 zau6 lai4!", english: "OK, coming right up!" },
        hint: "Thank the waiter.",
        acceptKeywords: ["thank", "唔該", "多謝"],
        teach: { cantonese: "唔該晒！", jyutping: "m4 goi1 saai3!", english: "Thank you very much!" },
      },
      {
        tutor: { cantonese: "食完啦？仲要唔要啲咩？", jyutping: "sik6 jyun4 laa3? zung6 jiu3 m4 jiu3 di1 me1?", english: "Done? Need anything else?" },
        hint: "Ask for the bill and how much it is.",
        acceptKeywords: ["bill", "check", "how much", "埋單", "幾多錢"],
        teach: { cantonese: "埋單，唔該。幾多錢呀？", jyutping: "maai4 daan1, m4 goi1. gei2 do1 cin2 aa3?", english: "The bill, please. How much is it?" },
      },
    ],
    likelyMistakes: [
      { mistake: "我要一個奶茶", correction: "我要一杯奶茶", explanation: "Drinks use the measure word 杯 bui1 (cup), not 個 go3." },
      { mistake: "不要冰 (Mandarin pattern)", correction: "走冰", explanation: "Hong Kong cafés say 走 zau2 + the thing to leave out: 走冰, 走甜, 走奶." },
      { mistake: "找錢 / 結帳", correction: "埋單", explanation: "埋單 maai4 daan1 is the universal Cantonese way to ask for the bill." },
    ],
    assessmentPhrases: [
      { cantonese: "唔該，我要一杯凍奶茶，少甜。", jyutping: "m4 goi1, ngo5 jiu3 jat1 bui1 dung3 naai5 caa4, siu2 tim4.", english: "Excuse me, an iced milk tea, less sweet." },
      { cantonese: "堂食，唔該。", jyutping: "tong4 sik6, m4 goi1.", english: "For here, please." },
      { cantonese: "埋單，唔該。幾多錢呀？", jyutping: "maai4 daan1, m4 goi1. gei2 do1 cin2 aa3?", english: "The bill, please. How much?" },
    ],
  },
  {
    id: "transport",
    title: "MTR, Taxis & Directions",
    subtitle: "Getting around Hong Kong without panic",
    icon: "🚇",
    color: "from-sky-500/20 to-blue-500/10",
    minutes: 6,
    setting: "You're heading to Mong Kok and need to ask for directions, then take a taxi.",
    objectives: [
      "Ask where the MTR station is",
      "Ask how to get to a destination",
      "Give a taxi driver your destination",
      "Understand basic direction words (轉左 / 直行)",
    ],
    targetPhrases: [
      { cantonese: "請問地鐵站喺邊呀？", jyutping: "cing2 man6 dei6 tit3 zaam6 hai2 bin1 aa3?", english: "Excuse me, where is the MTR station?" },
      { cantonese: "去旺角點搭呀？", jyutping: "heoi3 wong6 gok3 dim2 daap3 aa3?", english: "How do I get to Mong Kok?" },
      { cantonese: "要坐幾多個站？", jyutping: "jiu3 co5 gei2 do1 go3 zaam6?", english: "How many stops do I ride?" },
      { cantonese: "喺邊個站落車呀？", jyutping: "hai2 bin1 go3 zaam6 lok6 ce1 aa3?", english: "Which stop do I get off at?" },
      { cantonese: "唔該，去尖沙咀。", jyutping: "m4 goi1, heoi3 zim1 saa1 zeoi2.", english: "To Tsim Sha Tsui, please. (taxi)" },
      { cantonese: "喺前面路口停，唔該。", jyutping: "hai2 cin4 min6 lou6 hau2 ting4, m4 goi1.", english: "Stop at the junction ahead, please." },
      { cantonese: "轉左定轉右呀？", jyutping: "zyun2 zo2 ding6 zyun2 jau6 aa3?", english: "Turn left or turn right?" },
      { cantonese: "行路去遠唔遠呀？", jyutping: "haang4 lou6 heoi3 jyun5 m4 jyun5 aa3?", english: "Is it far on foot?" },
    ],
    openingLine: { cantonese: "咦，你好似搵緊路噃。要唔要幫手呀？", jyutping: "ji2, nei5 hou2 ci5 wan2 gan2 lou6 bo3. jiu3 m4 jiu3 bong1 sau2 aa3?", english: "Oh, you look like you're looking for directions. Need a hand?" },
    script: [
      {
        tutor: { cantonese: "你想去邊度呀？", jyutping: "nei5 soeng2 heoi3 bin1 dou6 aa3?", english: "Where do you want to go?" },
        hint: "Ask how to get to Mong Kok.",
        acceptKeywords: ["mong kok", "get to", "旺角", "how"],
        teach: { cantonese: "請問去旺角點搭呀？", jyutping: "cing2 man6 heoi3 wong6 gok3 dim2 daap3 aa3?", english: "Excuse me, how do I get to Mong Kok?" },
      },
      {
        tutor: { cantonese: "搭荃灣綫，坐三個站就到㗎啦。", jyutping: "daap3 cyun4 waan1 sin3, co5 saam1 go3 zaam6 zau6 dou3 gaa3 laa1.", english: "Take the Tsuen Wan line, three stops and you're there." },
        hint: "Ask which station to get off at / confirm the number of stops.",
        acceptKeywords: ["stop", "get off", "站", "how many"],
        teach: { cantonese: "唔該，喺邊個站落車呀？", jyutping: "m4 goi1, hai2 bin1 go3 zaam6 lok6 ce1 aa3?", english: "Excuse me, which stop do I get off at?" },
      },
      {
        tutor: { cantonese: "旺角站落車，B出口行出去就係。", jyutping: "wong6 gok3 zaam6 lok6 ce1, B ceot1 hau2 haang4 ceot1 heoi3 zau6 hai6.", english: "Get off at Mong Kok station, take Exit B and it's right there." },
        hint: "Thank them and ask if it's far on foot.",
        acceptKeywords: ["far", "walk", "thank", "遠", "唔該"],
        teach: { cantonese: "唔該晒！行路去遠唔遠呀？", jyutping: "m4 goi1 saai3! haang4 lou6 heoi3 jyun5 m4 jyun5 aa3?", english: "Thanks! Is it far on foot?" },
      },
      {
        tutor: { cantonese: "唔遠，五分鐘左右。", jyutping: "m4 jyun5, ng5 fan1 zung1 zo2 jau6.", english: "Not far, about five minutes." },
        hint: "Great — now get in a taxi and tell the driver: Tsim Sha Tsui, please.",
        acceptKeywords: ["tsim sha tsui", "taxi", "尖沙咀"],
        teach: { cantonese: "唔該，去尖沙咀。", jyutping: "m4 goi1, heoi3 zim1 saa1 zeoi2.", english: "To Tsim Sha Tsui, please." },
      },
      {
        tutor: { cantonese: "好，冇問題。", jyutping: "hou2, mou5 man6 tai4.", english: "Sure, no problem." },
        hint: "Ask the driver to stop at the junction ahead.",
        acceptKeywords: ["stop", "junction", "corner", "停"],
        teach: { cantonese: "喺前面路口停，唔該。", jyutping: "hai2 cin4 min6 lou6 hau2 ting4, m4 goi1.", english: "Stop at the junction ahead, please." },
      },
    ],
    likelyMistakes: [
      { mistake: "在哪裡？", correction: "喺邊呀？", explanation: "Spoken Cantonese: 喺邊 hai2 bin1, not 在哪裡. 喺 = at, 邊 = where." },
      { mistake: "去旺角怎麼搭？", correction: "去旺角點搭呀？", explanation: "點 dim2 (how) is the colloquial form; 怎麼 is Mandarin-style." },
      { mistake: "下車", correction: "落車", explanation: "Getting off transport is 落車 lok6 ce1 in Cantonese." },
    ],
    assessmentPhrases: [
      { cantonese: "請問地鐵站喺邊呀？", jyutping: "cing2 man6 dei6 tit3 zaam6 hai2 bin1 aa3?", english: "Where is the MTR station?" },
      { cantonese: "唔該，去尖沙咀。", jyutping: "m4 goi1, heoi3 zim1 saa1 zeoi2.", english: "To Tsim Sha Tsui, please." },
      { cantonese: "喺邊個站落車呀？", jyutping: "hai2 bin1 go3 zaam6 lok6 ce1 aa3?", english: "Which stop do I get off at?" },
    ],
  },
  {
    id: "shopping",
    title: "Shopping & Payments",
    subtitle: "Bargaining, sizes, and paying",
    icon: "🛍️",
    color: "from-fuchsia-500/20 to-pink-500/10",
    minutes: 6,
    setting: "A clothing shop at a market in Causeway Bay.",
    objectives: [
      "Ask the price of an item",
      "Ask for a discount politely",
      "Ask to try something on / for a different size",
      "Ask about payment methods",
    ],
    targetPhrases: [
      { cantonese: "呢件幾多錢呀？", jyutping: "ni1 gin6 gei2 do1 cin2 aa3?", english: "How much is this one?" },
      { cantonese: "有冇平啲呀？", jyutping: "jau5 mou5 peng4 di1 aa3?", english: "Can it be cheaper?", note: "Classic polite haggling." },
      { cantonese: "可唔可以試吓呀？", jyutping: "ho2 m4 ho2 ji5 si3 haa5 aa3?", english: "Can I try it on?" },
      { cantonese: "有冇大碼呀？", jyutping: "jau5 mou5 daai6 maa5 aa3?", english: "Do you have a large size?", note: "細碼 sai3 maa5 = small, 中碼 zung1 maa5 = medium." },
      { cantonese: "收唔收信用卡呀？", jyutping: "sau1 m4 sau1 seon3 jung6 kaat1 aa3?", english: "Do you take credit cards?" },
      { cantonese: "可以俾現金。", jyutping: "ho2 ji5 bei2 jin6 gam1.", english: "I can pay cash." },
      { cantonese: "唔該俾張單我。", jyutping: "m4 goi1 bei2 zoeng1 daan1 ngo5.", english: "Please give me the receipt." },
      { cantonese: "唔啱著，我想退貨。", jyutping: "m4 ngaam1 zoek3, ngo5 soeng2 teoi3 fo3.", english: "It doesn't fit, I'd like to return it." },
    ],
    openingLine: { cantonese: "靚仔/靚女，隨便睇吓啦！今日有折㗎。", jyutping: "leng3 zai2 / leng3 neoi5, ceoi4 bin6 tai2 haa5 laa1! gam1 jat6 jau5 zit3 gaa3.", english: "Handsome/pretty, take a look around! There's a discount today." },
    script: [
      {
        tutor: { cantonese: "想睇啲咩呀？T恤定褲？", jyutping: "soeng2 tai2 di1 me1 aa3? T seot1 ding6 fu3?", english: "What are you looking for? T-shirts or trousers?" },
        hint: "Ask how much this T-shirt is.",
        acceptKeywords: ["how much", "price", "幾多錢", "t-shirt"],
        teach: { cantonese: "呢件T恤幾多錢呀？", jyutping: "ni1 gin6 T seot1 gei2 do1 cin2 aa3?", english: "How much is this T-shirt?" },
      },
      {
        tutor: { cantonese: "兩百八十九蚊。", jyutping: "loeng5 baak3 baat3 sap6 gau2 man1.", english: "289 dollars." },
        hint: "Ask if it can be cheaper.",
        acceptKeywords: ["cheaper", "discount", "平"],
        teach: { cantonese: "有冇平啲呀？", jyutping: "jau5 mou5 peng4 di1 aa3?", english: "Can it be cheaper?" },
      },
      {
        tutor: { cantonese: "好啦，兩百五俾你啦。", jyutping: "hou2 laa1, loeng5 baak3 ng5 bei2 nei5 laa1.", english: "Alright, 250 for you." },
        hint: "Ask if you can try it on.",
        acceptKeywords: ["try", "試"],
        teach: { cantonese: "好呀，可唔可以試吓呀？", jyutping: "hou2 aa3, ho2 m4 ho2 ji5 si3 haa5 aa3?", english: "OK, can I try it on?" },
      },
      {
        tutor: { cantonese: "可以，試身室喺後面。", jyutping: "ho2 ji5, si3 san1 sat1 hai2 hau6 min6.", english: "Sure, the fitting room is at the back." },
        hint: "It fits! Ask if they take credit cards.",
        acceptKeywords: ["card", "credit", "pay", "信用咭", "信用卡"],
        teach: { cantonese: "收唔收信用卡呀？", jyutping: "sau1 m4 sau1 seon3 jung6 kaat1 aa3?", english: "Do you take credit cards?" },
      },
      {
        tutor: { cantonese: "收，碌卡冇問題。", jyutping: "sau1, luk1 kaat1 mou5 man6 tai4.", english: "Yes, cards are fine." },
        hint: "Say you'll take it and ask for the receipt.",
        acceptKeywords: ["take it", "receipt", "buy", "單"],
        teach: { cantonese: "我要呢件。唔該俾張單我。", jyutping: "ngo5 jiu3 ni1 gin6. m4 goi1 bei2 zoeng1 daan1 ngo5.", english: "I'll take this one. Please give me the receipt." },
      },
    ],
    likelyMistakes: [
      { mistake: "便宜嗎？", correction: "有冇平啲呀？", explanation: "平 peng4 is the spoken word for cheap; 便宜 is written/Mandarin register." },
      { mistake: "試穿", correction: "試吓 / 試身", explanation: "Colloquially you 試吓 si3 haa5 (try a bit); fitting room is 試身室." },
      { mistake: "信用卡… credit card tone slip: kaat1 vs kaat3", correction: "kaat1 (high level)", explanation: "卡 is tone 1 (high level); dropping it to a low tone can sound like a different word." },
    ],
    assessmentPhrases: [
      { cantonese: "呢件幾多錢呀？", jyutping: "ni1 gin6 gei2 do1 cin2 aa3?", english: "How much is this?" },
      { cantonese: "有冇平啲呀？", jyutping: "jau5 mou5 peng4 di1 aa3?", english: "Can it be cheaper?" },
      { cantonese: "收唔收信用卡呀？", jyutping: "sau1 m4 sau1 seon3 jung6 kaat1 aa3?", english: "Do you take credit cards?" },
    ],
  },
  {
    id: "workplace",
    title: "Workplace Small Talk",
    subtitle: "Office chat, meetings, after-work plans",
    icon: "💼",
    color: "from-violet-500/20 to-purple-500/10",
    minutes: 6,
    setting: "Monday morning at the office pantry with your colleague Ka Yan.",
    objectives: [
      "Greet colleagues in the morning",
      "Ask about weekend and workload",
      "Talk about meetings and deadlines",
      "Invite a colleague to lunch or after-work drinks",
    ],
    targetPhrases: [
      { cantonese: "早晨！飲咗咖啡未呀？", jyutping: "zou2 san4! jam2 zo2 gaa3 fe1 mei6 aa3?", english: "Morning! Had your coffee yet?" },
      { cantonese: "你週末去咗邊度玩呀？", jyutping: "nei5 zau1 mut6 heoi3 zo2 bin1 dou6 waan2 aa3?", english: "Where did you go on the weekend?" },
      { cantonese: "今日忙唔忙呀？", jyutping: "gam1 jat6 mong4 m4 mong4 aa3?", english: "Busy today?" },
      { cantonese: "個會改咗期，改去星期三。", jyutping: "go3 wui2 goi2 zo2 kei4, goi2 heoi3 sing1 kei4 saam1.", english: "The meeting was rescheduled to Wednesday." },
      { cantonese: "份報告我趕緊，今日交得切。", jyutping: "fan6 bou3 gou3 ngo5 gon2 gan2, gam1 jat6 gaau1 dak1 cit3.", english: "I'm rushing the report; I can hand it in today." },
      { cantonese: "唔該幫我睇睇呢個email。", jyutping: "m4 goi1 bong1 ngo5 tai2 tai2 ni1 go3 email.", english: "Please help me take a look at this email." },
      { cantonese: "放工一齊食飯好唔好？", jyutping: "fong3 gung1 jat1 cai4 sik6 faan6 hou2 m4 hou2?", english: "Want to grab dinner after work?" },
      { cantonese: "辛苦晒！聽日見。", jyutping: "san1 fu2 saai3! ting1 jat6 gin3.", english: "Good work today (literally 'hard work')! See you tomorrow." },
    ],
    openingLine: { cantonese: "早晨！週末過得點呀？", jyutping: "zou2 san4! zau1 mut6 gwo3 dak1 dim2 aa3?", english: "Morning! How was your weekend?" },
    script: [
      {
        tutor: { cantonese: "週末過得點呀？", jyutping: "zau1 mut6 gwo3 dak1 dim2 aa3?", english: "How was your weekend?" },
        hint: "Say it was good and ask about hers.",
        acceptKeywords: ["good", "weekend", "you", "你呢"],
        teach: { cantonese: "幾好呀！你呢？", jyutping: "gei2 hou2 aa3! nei5 ne1?", english: "Pretty good! And you?" },
      },
      {
        tutor: { cantonese: "我留咗喺屋企休息。你今日忙唔忙呀？", jyutping: "ngo5 lau4 zo2 hai2 uk1 kei2 jau1 sik1. nei5 gam1 jat6 mong4 m4 mong4 aa3?", english: "I stayed home and rested. Are you busy today?" },
        hint: "Say you are quite busy, you are rushing a report.",
        acceptKeywords: ["busy", "report", "忙", "報告"],
        teach: { cantonese: "幾忙呀，我趕緊份報告。", jyutping: "gei2 mong4 aa3, ngo5 gon2 gan2 fan6 bou3 gou3.", english: "Quite busy, I'm rushing a report." },
      },
      {
        tutor: { cantonese: "哦，個會改咗去星期三，你知唔知呀？", jyutping: "o3, go3 wui2 goi2 zo2 heoi3 sing1 kei4 saam1, nei5 zi1 m4 zi1 aa3?", english: "Oh, the meeting moved to Wednesday — did you know?" },
        hint: "Say you didn't know, thank her.",
        acceptKeywords: ["didn't", "know", "thank", "唔知", "唔該"],
        teach: { cantonese: "哦，我唔知喎，唔該你話我知！", jyutping: "o3, ngo5 m4 zi1 wo3, m4 goi1 nei5 waa6 ngo5 zi1!", english: "Oh, I didn't know — thanks for telling me!" },
      },
      {
        tutor: { cantonese: "唔緊要。對啦，今晚放工有咩安排呀？", jyutping: "m4 gan1 jiu3. deoi3 laa1, gam1 maan5 fong3 gung1 jau5 me1 on1 paai4 aa3?", english: "No worries. By the way, any plans after work tonight?" },
        hint: "Invite her to have dinner together.",
        acceptKeywords: ["dinner", "eat", "together", "食飯", "一齊"],
        teach: { cantonese: "放工一齊食飯好唔好？", jyutping: "fong3 gung1 jat1 cai4 sik6 faan6 hou2 m4 hou2?", english: "How about dinner together after work?" },
      },
      {
        tutor: { cantonese: "好呀！樓下新開咗間茶餐廳，試吓？", jyutping: "hou2 aa3! lau4 haa6 san1 hoi1 zo2 gaan1 caa4 caan1 teng1, si3 haa5?", english: "Sure! A new cha chaan teng opened downstairs — want to try?" },
        hint: "Agree and say see you later.",
        acceptKeywords: ["yes", "ok", "sure", "see you", "好", "陣間見"],
        teach: { cantonese: "好呀，陣間見！", jyutping: "hou2 aa3, zan6 gaan1 gin3!", english: "Great, see you in a bit!" },
      },
    ],
    likelyMistakes: [
      { mistake: "下班後", correction: "放工", explanation: "After work is 放工 fong3 gung1 in spoken Cantonese; 下班 is written style." },
      { mistake: "一起", correction: "一齊", explanation: "Together is 一齊 jat1 cai4, not 一起 jat1 hei2." },
      { mistake: "謝謝你告訴我", correction: "唔該你話我知", explanation: "Tell is 話 waa6 in Cantonese; 告訴 is formal written register." },
    ],
    assessmentPhrases: [
      { cantonese: "你週末去咗邊度玩呀？", jyutping: "nei5 zau1 mut6 heoi3 zo2 bin1 dou6 waan2 aa3?", english: "Where did you go on the weekend?" },
      { cantonese: "今日忙唔忙呀？", jyutping: "gam1 jat6 mong4 m4 mong4 aa3?", english: "Busy today?" },
      { cantonese: "放工一齊食飯好唔好？", jyutping: "fong3 gung1 jat1 cai4 sik6 faan6 hou2 m4 hou2?", english: "Dinner together after work?" },
    ],
  },
  {
    id: "social",
    title: "Making Friends & Social Talk",
    subtitle: "Hobbies, plans, hotpot invitations",
    icon: "🍲",
    color: "from-rose-500/20 to-red-500/10",
    minutes: 6,
    setting: "You meet a new friend, Wing, at a board-game night in Sheung Wan.",
    objectives: [
      "Ask about hobbies and free time",
      "Talk about where you live",
      "Make social plans (hotpot, drinks, hiking)",
      "Exchange contact / arrange to meet again",
    ],
    targetPhrases: [
      { cantonese: "你平時鍾意做咩呀？", jyutping: "nei5 ping4 si4 zung1 ji3 zou6 me1 aa3?", english: "What do you like doing in your free time?" },
      { cantonese: "我鍾意行山同食好嘢。", jyutping: "ngo5 zung1 ji3 haang4 saan1 tung4 sik6 hou2 je5.", english: "I like hiking and eating good food." },
      { cantonese: "你住喺邊區呀？", jyutping: "nei5 zyu6 hai2 bin1 keoi1 aa3?", english: "Which district do you live in?" },
      { cantonese: "我住西環，交通幾方便。", jyutping: "ngo5 zyu6 sai1 waan4, gaau1 tung1 gei2 fong1 bin6.", english: "I live in Sai Wan, transport is quite convenient." },
      { cantonese: "改日一齊打邊爐好唔好？", jyutping: "goi2 jat6 jat1 cai4 daa2 bin1 lou4 hou2 m4 hou2?", english: "How about hotpot together some day?" },
      { cantonese: "得閒出嚟飲嘢呀！", jyutping: "dak1 haan4 ceot1 lai4 jam2 je5 aa3!", english: "Come out for drinks when you're free!" },
      { cantonese: "我send我個電話號碼俾你。", jyutping: "ngo5 send ngo5 go3 din6 waa2 hou6 maa5 bei2 nei5.", english: "I'll send you my phone number." },
      { cantonese: "下次再約，保持聯絡！", jyutping: "haa6 ci3 zoi3 joek3, bou2 ci4 lyun4 lok3!", english: "Let's meet again, keep in touch!" },
    ],
    openingLine: { cantonese: "你好！我係阿Wing，你係第一次嚟board game night？", jyutping: "nei5 hou2! ngo5 hai6 aa3 Wing, nei5 hai6 dai6 jat1 ci3 lai4 board game night?", english: "Hi! I'm Wing — is this your first board game night?" },
    script: [
      {
        tutor: { cantonese: "你係第一次嚟呀？你平時鍾意玩咩game呀？", jyutping: "nei5 hai6 dai6 jat1 ci3 lai4 aa3? nei5 ping4 si4 zung1 ji3 waan2 me1 game aa3?", english: "First time here? What games do you usually like?" },
        hint: "Say yes it's your first time, and you like strategy games.",
        acceptKeywords: ["first", "strategy", "yes", "第一次"],
        teach: { cantonese: "係呀，第一次。我鍾意玩策略遊戲。", jyutping: "hai6 aa3, dai6 jat1 ci3. ngo5 zung1 ji3 waan2 caak3 loek6 jau4 hei3.", english: "Yes, first time. I like strategy games." },
      },
      {
        tutor: { cantonese: "除咗玩game，你仲鍾意做咩呀？", jyutping: "ceoi4 zo2 waan2 game, nei5 zung6 zung1 ji3 zou6 me1 aa3?", english: "Besides games, what else do you like doing?" },
        hint: "Say you like hiking and eating good food.",
        acceptKeywords: ["hiking", "food", "eat", "行山"],
        teach: { cantonese: "我鍾意行山同食好嘢。", jyutping: "ngo5 zung1 ji3 haang4 saan1 tung4 sik6 hou2 je5.", english: "I like hiking and eating good food." },
      },
      {
        tutor: { cantonese: "行山正呀！你住喺邊區呀？", jyutping: "haang4 saan1 zeng3 aa3! nei5 zyu6 hai2 bin1 keoi1 aa3?", english: "Hiking is awesome! Which district do you live in?" },
        hint: "Say which area you live in.",
        acceptKeywords: ["live", "sai wan", "wan chai", "住"],
        teach: { cantonese: "我住西環。", jyutping: "ngo5 zyu6 sai1 waan4.", english: "I live in Sai Wan." },
      },
      {
        tutor: { cantonese: "西環幾好呀，好多好嘢食！", jyutping: "sai1 waan4 gei2 hou2 aa3, hou2 do1 hou2 je5 sik6!", english: "Sai Wan is nice, lots of good food!" },
        hint: "Invite her to hotpot some day.",
        acceptKeywords: ["hotpot", "打邊爐", "invite", "together"],
        teach: { cantonese: "改日一齊打邊爐好唔好？", jyutping: "goi2 jat6 jat1 cai4 daa2 bin1 lou4 hou2 m4 hou2?", english: "How about hotpot together some day?" },
      },
      {
        tutor: { cantonese: "好呀！你send個電話號碼俾我啦。", jyutping: "hou2 aa3! nei5 send go3 din6 waa2 hou6 maa5 bei2 ngo5 laa1.", english: "Sure! Send me your number." },
        hint: "Say you'll send it, and keep in touch.",
        acceptKeywords: ["send", "number", "touch", "聯絡", "好"],
        teach: { cantonese: "好，我send俾你。保持聯絡！", jyutping: "hou2, ngo5 send bei2 nei5. bou2 ci4 lyun4 lok3!", english: "OK, I'll send it to you. Keep in touch!" },
      },
    ],
    likelyMistakes: [
      { mistake: "喜歡", correction: "鍾意", explanation: "Like is 鍾意 zung1 ji3 in spoken Cantonese; 喜歡 hei2 fun1 is written form." },
      { mistake: "火鍋", correction: "打邊爐", explanation: "In Hong Kong you say 打邊爐 daa2 bin1 lou4 for hotpot, never 火鍋 in casual speech." },
      { mistake: "有空 (written)", correction: "得閒", explanation: "Free time is 得閒 dak1 haan4 in colloquial Cantonese." },
    ],
    assessmentPhrases: [
      { cantonese: "你平時鍾意做咩呀？", jyutping: "nei5 ping4 si4 zung1 ji3 zou6 me1 aa3?", english: "What do you like doing?" },
      { cantonese: "改日一齊打邊爐好唔好？", jyutping: "goi2 jat6 jat1 cai4 daa2 bin1 lou4 hou2 m4 hou2?", english: "Hotpot together some day?" },
      { cantonese: "下次再約，保持聯絡！", jyutping: "haa6 ci3 zoi3 joek3, bou2 ci4 lyun4 lok3!", english: "Meet again, keep in touch!" },
    ],
  },
  {
    id: "emergency",
    title: "Emergency & Medical Basics",
    subtitle: "Getting help, seeing a doctor, pharmacy",
    icon: "🏥",
    color: "from-red-500/20 to-orange-500/10",
    minutes: 5,
    setting: "You feel unwell and need to see a doctor in Hong Kong.",
    objectives: [
      "Say you feel unwell and describe symptoms",
      "Ask to see a doctor / find a pharmacy",
      "State allergies",
      "Ask for urgent help",
    ],
    targetPhrases: [
      { cantonese: "我唔舒服。", jyutping: "ngo5 m4 syu1 fuk6.", english: "I don't feel well." },
      { cantonese: "我想睇醫生。", jyutping: "ngo5 soeng2 tai2 ji1 sang1.", english: "I'd like to see a doctor.", note: "睇醫生 tai2 ji1 sang1 = see a doctor (colloquial)." },
      { cantonese: "我頭痛，仲有啲發燒。", jyutping: "ngo5 tau4 tung3, zung6 jau5 di1 faat3 siu1.", english: "I have a headache and a bit of a fever." },
      { cantonese: "我對花生敏感。", jyutping: "ngo5 deoi3 faa1 sang1 man5 gam2.", english: "I'm allergic to peanuts." },
      { cantonese: "藥房喺邊度呀？", jyutping: "joek6 fong4 hai2 bin1 dou6 aa3?", english: "Where is the pharmacy?" },
      { cantonese: "唔該幫我叫救護車！", jyutping: "m4 goi1 bong1 ngo5 giu3 gau3 wu6 ce1!", english: "Please call an ambulance for me!" },
      { cantonese: "呢度好痛。", jyutping: "ni1 dou6 hou2 tung3.", english: "It hurts a lot here." },
      { cantonese: "我唔見咗銀包，想報警。", jyutping: "ngo5 m4 gin3 zo2 ngan4 baau1, soeng2 bou2 ging2.", english: "I lost my wallet and want to report to the police." },
    ],
    openingLine: { cantonese: "你面色唔多好喎，有冇事呀？", jyutping: "nei5 min6 sik1 m4 do1 hou2 wo3, jau5 mou5 si6 aa3?", english: "You don't look well — are you OK?" },
    script: [
      {
        tutor: { cantonese: "你面色唔好喎，有冇事呀？", jyutping: "nei5 min6 sik1 m4 hou2 wo3, jau5 mou5 si6 aa3?", english: "You look pale — are you OK?" },
        hint: "Say you don't feel well and want to see a doctor.",
        acceptKeywords: ["not well", "unwell", "doctor", "sick", "唔舒服", "醫生"],
        teach: { cantonese: "我唔舒服，我想睇醫生。", jyutping: "ngo5 m4 syu1 fuk6, ngo5 soeng2 tai2 ji1 sang1.", english: "I don't feel well, I'd like to see a doctor." },
      },
      {
        tutor: { cantonese: "你邊度唔舒服呀？", jyutping: "nei5 bin1 dou6 m4 syu1 fuk6 aa3?", english: "Where do you feel unwell?" },
        hint: "Describe a symptom (headache / fever / stomach ache).",
        acceptKeywords: ["headache", "fever", "stomach", "頭痛", "發燒", "肚痛"],
        teach: { cantonese: "我頭痛，仲有啲發燒。", jyutping: "ngo5 tau4 tung3, zung6 jau5 di1 faat3 siu1.", english: "I have a headache and a bit of a fever." },
      },
      {
        tutor: { cantonese: "有冇藥物敏感呀？", jyutping: "jau5 mou5 joek6 mat6 man5 gam2 aa3?", english: "Any drug allergies?" },
        hint: "Say you are allergic to peanuts (or say no allergies).",
        acceptKeywords: ["allergic", "peanut", "no", "敏感"],
        teach: { cantonese: "我對花生敏感。", jyutping: "ngo5 deoi3 faa1 sang1 man5 gam2.", english: "I'm allergic to peanuts." },
      },
      {
        tutor: { cantonese: "前面轉角有間診所。要唔要我陪你去呀？", jyutping: "cin4 min6 zyun2 gok3 jau5 gaan1 can2 so2. jiu3 m4 jiu3 ngo5 pui4 nei5 heoi3 aa3?", english: "There's a clinic around the corner. Want me to go with you?" },
        hint: "Thank them and say yes / no thanks.",
        acceptKeywords: ["thank", "yes", "no", "唔該", "好"],
        teach: { cantonese: "唔該晒你，麻煩你陪我。", jyutping: "m4 goi1 saai3 nei5, maa4 faan4 nei5 pui4 ngo5.", english: "Thank you so much, please come with me." },
      },
    ],
    likelyMistakes: [
      { mistake: "看醫生", correction: "睇醫生", explanation: "See/watch is 睇 tai2 in Cantonese; 看 hon3 is written register." },
      { mistake: "救護車 vs 白車", correction: "both fine — 白車 is slang", explanation: "救護車 gau3 wu6 ce1 is standard; 白車 baak3 ce1 ('white car') is very common slang in HK." },
      { mistake: "錢包", correction: "銀包", explanation: "Wallet is 銀包 ngan4 baau1 in Cantonese, not 錢包." },
    ],
    assessmentPhrases: [
      { cantonese: "我唔舒服，我想睇醫生。", jyutping: "ngo5 m4 syu1 fuk6, ngo5 soeng2 tai2 ji1 sang1.", english: "I don't feel well, I want to see a doctor." },
      { cantonese: "我對花生敏感。", jyutping: "ngo5 deoi3 faa1 sang1 man5 gam2.", english: "I'm allergic to peanuts." },
      { cantonese: "唔該幫我叫救護車！", jyutping: "m4 goi1 bong1 ngo5 giu3 gau3 wu6 ce1!", english: "Please call an ambulance!" },
    ],
  },
  {
    id: "free-talk",
    title: "Free Talk",
    subtitle: "No script — talk about anything, in any mix",
    icon: "💬",
    color: "from-lime-500/20 to-green-500/10",
    minutes: 10,
    setting: "An open conversation with your tutor persona — your day, your interests, anything.",
    objectives: [
      "Sustain an open-ended conversation",
      "Ask for Cantonese versions of whatever you want to say",
      "Mix English and Cantonese naturally",
    ],
    targetPhrases: [
      { cantonese: "「...」廣東話點講呀？", jyutping: "... gwong2 dung1 waa2 dim2 gong2 aa3?", english: "How do you say \"...\" in Cantonese?" },
      { cantonese: "我聽唔明，可唔可以講慢啲？", jyutping: "ngo5 teng1 m4 ming4, ho2 m4 ho2 ji5 gong2 maan6 di1?", english: "I don't understand — can you speak slower?" },
      { cantonese: "呢個字點讀呀？", jyutping: "ni1 go3 zi6 dim2 duk6 aa3?", english: "How do you pronounce this character?" },
    ],
    openingLine: { cantonese: "哈囉！今日想傾咩呀？講英文都得，我幫你變廣東話。", jyutping: "haa1 lou3! gam1 jat6 soeng2 king1 me1 aa3? gong2 jing1 man2 dou1 dak1, ngo5 bong1 nei5 bin3 gwong2 dung1 waa2.", english: "Hi! What shall we chat about today? English is fine — I'll turn it into Cantonese for you." },
    script: [],
    likelyMistakes: [],
    assessmentPhrases: [],
  },
];

export function getScenario(id: string): Scenario | undefined {
  return SCENARIOS.find((s) => s.id === id);
}

/** All phrases across scenarios, for global drills and the phrasebook seed. */
export function allTargetPhrases(): (PhraseItem & { scenarioId: string })[] {
  return SCENARIOS.flatMap((s) =>
    s.targetPhrases.map((p) => ({ ...p, scenarioId: s.id })),
  );
}
