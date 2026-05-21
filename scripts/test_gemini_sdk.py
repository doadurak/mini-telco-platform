from backend.config import settings

try:
    from google import genai
except ImportError as exc:
    raise SystemExit(f"google-genai is not installed: {exc}") from exc


def main() -> None:
    if not settings.gemini_api_key:
        raise SystemExit("GEMINI_API_KEY is not configured.")

    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents="Explain how AI works in a few words.",
    )
    print(response.text)


if __name__ == "__main__":
    main()
