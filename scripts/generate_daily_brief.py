from datetime import date

from app.recommendations.market_brief import generate_market_brief


def main() -> None:
    brief = generate_market_brief(context={"key_news": [], "sources": []}, as_of=date.today())
    print(brief.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
