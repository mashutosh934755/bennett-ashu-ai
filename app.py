def handle_user_query(prompt):
    # Book search intent (simple heuristic)
    if "find books on" in prompt.lower() or "find book on" in prompt.lower():
        topic = (
            prompt.lower()
            .replace("find books on", "")
            .replace("find book on", "")
            .strip()
        )
        topic = topic if topic else "library"
        answer = f"### 📚 Books on **{topic.title()}**\n"

        # 1) Koha (real-time Bennett OPAC)
        koha = koha_search_biblios(topic, limit=5)
        answer += "#### Bennett OPAC (Koha)\n"
        if koha["records"]:
            for book in koha["records"]:
                authors = f" by {book['authors']}" if book.get("authors") else ""
                answer += f"- [{book['title']}]({book['url']}){authors}\n"
        else:
            answer += f"- *(API search unavailable on this server build)* — Please use OPAC: [{topic}]({koha['opac_url']})\n"

        # 2) Google Books
        gb = google_books_search(topic, limit=5)
        answer += "\n#### Google Books\n"
        if gb:
            for book in gb:
                authors = f" by {book['authors']}" if book['authors'] else ""
                pub = f", {book['publisher']}" if book['publisher'] else ""
                year = f" ({book['year']})" if book['year'] else ""
                answer += f"- [{book['title']}]({book['url']}){authors}{pub}{year}\n"
        else:
            answer += "- No relevant books found from Google Books.\n"

        answer += f"\n**More:** [BU OPAC](https://libraryopac.bennett.edu.in/) · [Refread e-Resources](https://bennett.refread.com/#/home)\n"
        return answer

    # Article / research paper intent
    article_keywords = [
        "article", "articles", "research paper", "journal", "preprint", "open access", "dataset",
        "साहित्य", "आर्टिकल", "पत्रिका", "जर्नल", "शोध", "पेपर"
    ]
    if any(kw in prompt.lower() for kw in article_keywords):
        topic = get_topic_from_prompt(prompt)
        if not topic or len(topic) < 2:
            return "Please specify a topic for article search. उदाहरण: 'articles on AI' या 'हिंदी साहित्य पर articles'।"
        topic = topic.strip()

        answer = f"### 🟦 Bennett University e-Resources (Refread)\n"
        answer += f"Find e-books and journal articles on **'{topic.title()}'** 24/7 here: [Refread](https://bennett.refread.com/#/home)\n\n"

        # Optional: Koha titles on topic (real-time)
        koha = koha_search_biblios(topic, limit=5)
        answer += "#### Bennett OPAC (Koha)\n"
        if koha["records"]:
            for book in koha["records"]:
                authors = f" by {book['authors']}" if book.get("authors") else ""
                answer += f"- [{book['title']}]({book['url']}){authors}\n"
        else:
            answer += f"- *(API search unavailable on this server build)* — Try OPAC: [{topic}]({koha['opac_url']})\n"

        # Google Books
        google_books = google_books_search(topic, limit=3)
        answer += "\n#### Google Books\n"
        if google_books:
            for book in google_books:
                authors = f" by {book['authors']}" if book['authors'] else ""
                pub = f", {book['publisher']}" if book['publisher'] else ""
                year = f" ({book['year']})" if book['year'] else ""
                answer += f"- [{book['title']}]({book['url']}){authors}{pub}{year}\n"
        else:
            answer += "- No relevant books found from Google Books.\n"

        # CORE / arXiv / DOAJ / DataCite (unchanged)
        core_results = core_article_search(topic, limit=3)
        answer += "#### 🌐 CORE (Open Access)\n"
        if core_results:
            for art in core_results:
                title = art.get("title", "No Title")
                url = art.get("downloadUrl", art.get("urls", [{}])[0].get("url", "#"))
                year = art.get("createdDate", "")[:4]
                answer += f"- [{title}]({url}) {'('+year+')' if year else ''}\n"
        else:
            answer += "- No recent OA articles found on CORE.\n"

        arxiv_results = arxiv_article_search(topic, limit=3)
        answer += "#### 📄 arXiv (Preprints)\n"
        if arxiv_results:
            for art in arxiv_results:
                answer += f"- [{art['title']}]({art['url']}) ({art['year']})\n"
        else:
            answer += "- No preprints found on arXiv.\n"

        doaj_results = doaj_article_search(topic, limit=3)
        answer += "#### 📚 DOAJ (Open Access Journals)\n"
        if doaj_results:
            for art in doaj_results:
                answer += f"- [{art['title']}]({art['url']}) ({art['year']}) - {art['journal']}\n"
        else:
            answer += "- No OA journal articles found on DOAJ.\n"

        datacite_results = datacite_article_search(topic, limit=3)
        answer += "#### 🏷️ DataCite\n"
        if datacite_results:
            for art in datacite_results:
                answer += f"- [{art['title']}]({art['url']}) ({art['year']}) - {art['journal']}\n"
        else:
            answer += "- No entries found on DataCite.\n"

        return answer

    # General (FAQ etc) via Gemini (unchanged)
    payload = create_payload(prompt)
    return call_gemini_api_v2(payload)
