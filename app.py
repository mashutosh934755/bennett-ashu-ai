<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ashu AI – Bennett Library Voice Assistant</title>
    <link rel="icon" type="image/png" href="robotface.png">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Bitcount+Prop+Single:wght@100..900&display=swap');
        body {
            width: 100vw; height: 100vh; background: #090b10; margin: 0;
            display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 18px;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        #logo { width: 120px; }
        h1 { color: #f0f8ff; font-family: "Bitcount Prop Single", system-ui; font-size: 1.7em; }
        #name { color: #ff0404; font-size: 40px; }
        #va { color: #374ef7; font-size: 40px; }
        #voice { width: 200px; display: none; }
        #btn {
            background: linear-gradient(to right, #f04444, #607ac6);
            color: white; border: none; border-radius: 22px;
            font-size: 1.1em; font-weight: 600; padding: 14px 36px;
            display: flex; align-items: center; gap: 13px; cursor: pointer;
            box-shadow: 0 2px 10px #f0444460, 0 2px 10px #607ac660;
            transition: 0.3s;
        }
        #btn img { width: 32px; }
        #btn:hover { letter-spacing: 1px; box-shadow: 0 5px 20px #607ac688; }
        #response {
            min-height: 60px; background: #181a20; color: #fff;
            border-radius: 11px; padding: 15px; margin-top: 13px; max-width: 480px; text-align: left;
            box-shadow: 0 2px 10px #0001;
        }
        @media (max-width: 600px) { #logo { width: 85px; } #name, #va { font-size: 30px; } }
    </style>
</head>
<body>
    <img src="robotface.png" alt="Ashu AI logo" id="logo">
    <h1>I'm <span id="name">Ashu AI</span>, your <span id="va">VOICE ASSISTANT</span></h1>
    <img src="voice.gif" id="voice" alt="listening...">
    <button id="btn">
        <img src="mic-02-stroke-rounded.svg" alt="mic">
        <span>Click &amp; Speak Your Query</span>
    </button>
    <div id="response"></div>

<script>
// ========== FAQ Knowledgebase ==========
const faqMap = [
    { keywords: ['issue', 'borrow', 'check-out'], answer: 'You may issue or borrow books through automated kiosks installed in the library.' },
    { keywords: ['return', 'drop box'], answer: 'You may return the books 24×7 at the Drop Box just outside the library.' },
    { keywords: ['overdue'], answer: 'Automated overdue mails are sent to you; you can also check it by logging into OPAC at https://libraryopac.bennett.edu.in/.' },
    { keywords: ['journal articles', 'articles', 'remote access'], answer: 'Yes, you have remote access to our digital library 24×7 at https://bennett.refread.com/#/home.' },
    { keywords: ['printers', 'scanners', 'fax'], answer: 'Printing and scanning facilities are available in the LRC from 09:00 AM to 05:30 PM.' },
    { keywords: ['alumni'], answer: 'Alumni are always welcome and may access the library for reference.' },
    { keywords: ['laptop', 'printers from my laptop'], answer: 'For official printouts, email your document to libraryhelpdesk@bennett.edu.in and collect the print from the centre.' },
    { keywords: ['how many books', 'checked-out'], answer: 'The number of books you can check out depends on your membership category. Please refer to the library’s borrowing policies for details.' },
    { keywords: ['pay my overdue', 'fine'], answer: 'Overdue fines can be paid through the BU Payment Portal; please update the library staff after payment.' },
    { keywords: ['recommend', 'purchase'], answer: 'Yes, you may recommend a book for purchase. Fill in the recommendation form provided by the library.' },
    { keywords: ['appeal'], answer: 'Please contact the library helpdesk at libraryhelpdesk@bennett.edu.in or visit the helpdesk in person.' },
    { keywords: ['download ebook', 'download e-book'], answer: 'To download chapters from e-books, visit https://bennett.refread.com/#/home.' },
    { keywords: ['inter library', 'loan'], answer: 'The library may arrange an interlibrary loan through DELNET. Contact the library staff for more information.' },
    { keywords: ['non bennett', 'non-Bennett'], answer: 'Non-Bennett users may use the library for reading purposes but cannot check out books.' },
    { keywords: ['find books', 'bookshelves'], answer: 'Search for a book through the OPAC. Each book has a call number which corresponds to the labels on the shelves.' },
    { keywords: ['snacks', 'eatables'], answer: 'Eatables are not allowed inside the LRC premises, but you may carry water bottles.' },
    { keywords: ['account still shows', 'checked out'], answer: 'If your account still shows a book as checked out, please contact the helpdesk or email libraryhelpdesk@bennett.edu.in.' },
    { keywords: ['reserve', 'place hold'], answer: 'If all copies of a book are issued, you may reserve it using the “Place Hold” feature in the OPAC.' },
    // Greetings!
    { keywords: ['hello', 'hi', 'hey', 'namaste', 'who are you', 'your name'], answer: 'Hello! I am Ashu, your voice assistant for Bennett University Library. How can I help you?' },
];

// Your Gemini API key (optional)
const GEMINI_API_KEY = "";  // fill your Gemini API key here if you want LLM fallback

// DOM references
const btn = document.querySelector('#btn');
const voiceIndicator = document.querySelector('#voice');
const responseBox = document.querySelector('#response');

// Speak out a given text
function speak(text) {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1; utterance.volume = 1; utterance.pitch = 1;
    window.speechSynthesis.speak(utterance);
}

// On load: Greet user
window.addEventListener('load', () => {
    speak('Welcome to Bennett University Library. I am Ashu AI. Click the microphone button and ask your library question.');
});

// FAQ lookup
function lookupFaq(question) {
    const lower = question.toLowerCase();
    for (const entry of faqMap) {
        if (entry.keywords.some(key => lower.includes(key))) return entry.answer;
    }
    return null;
}

// Gemini fallback (optional)
async function fetchGeminiAnswer(prompt) {
    if (!GEMINI_API_KEY) return null;
    const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=${GEMINI_API_KEY}`;
    const body = {
        contents: [
            { role: 'user', parts: [ { text: prompt } ] }
        ]
    };
    try {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (!res.ok) return null;
        const data = await res.json();
        return data?.candidates?.[0]?.content?.parts?.[0]?.text || null;
    } catch (err) {
        return null;
    }
}

// Core query handler
async function handleVoiceQuery(query) {
    responseBox.textContent = '';
    if (!query.trim()) return;
    let answer = lookupFaq(query.trim());
    if (!answer) answer = await fetchGeminiAnswer(query.trim());
    if (!answer) answer = 'Sorry, I do not know the answer to that. Please contact libraryhelpdesk@bennett.edu.in for assistance.';
    responseBox.textContent = answer;
    speak(answer);
}

// Voice recognition setup
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const recognition = SpeechRecognition ? new SpeechRecognition() : null;
if (recognition) {
    recognition.onresult = event => {
        const transcript = event.results[event.resultIndex][0].transcript;
        handleVoiceQuery(transcript);
    };
    recognition.onstart = () => { voiceIndicator.style.display = 'block'; };
    recognition.onend = () => { voiceIndicator.style.display = 'none'; };
}

btn.addEventListener('click', () => {
    if (recognition) recognition.start();
    else alert('Speech recognition is not supported on this device.');
});
</script>
</body>
</html>
