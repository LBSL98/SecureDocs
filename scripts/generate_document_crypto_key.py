from app.security.crypto import generate_document_crypto_key


def main() -> None:
    print(generate_document_crypto_key())


if __name__ == "__main__":
    main()
