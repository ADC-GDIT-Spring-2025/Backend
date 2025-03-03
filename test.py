from util.enron_parser import EnronMaildirParser


def main():
    parser = EnronMaildirParser("data/maildir")
    parser.process_maildir(max_emails=1000)

    folder_structure = parser.get_folder_structure()
    print("Folder structure:")
    for folder, emails in folder_structure.items():
        print(f"{folder}: {len(emails)} emails")

    # print the total number of emails processed and the total number of threads
    print(f"Total emails processed: {parser.stats.total_emails}")
    print(f"Total threads found: {parser.stats.total_threads}")


if __name__ == "__main__":
    main()