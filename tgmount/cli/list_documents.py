from argparse import ArgumentParser
from typing import Optional

from telethon import hints
from tgmount.tgmount.file_factory import FileFactoryDefault

from tgmount import tgclient
from tgmount import util
from tgmount.tgclient import TgmountTelegramClient
from tgmount.tgclient.guards import MessageDownloadable
from tgmount.tgmount.file_factory.classifier import ClassifierDefault
from tgmount.tgmount.file_factory.classifierbase import ClassifierBase
from tgmount.tgmount.filters import OnlyUniqueDocs
from tgmount.tgmount.tgmount_builder import MyFileFactoryDefault


async def list_documents(
    client: TgmountTelegramClient,
    entity: hints.EntityLike,
    *,
    limit: Optional[int] = None,
    reverse: bool = False,
    include_unsupported=True,
    print_message_object=True,
    only_unsupported=False,
    print_all_matching_types=False,
    only_unique_docs=False,
    print_sender=True,
):
    factory = MyFileFactoryDefault(
        files_source=tgclient.TelegramFilesSource(client),
    )

    classifier = ClassifierDefault()

    messages = await client.get_messages(
        entity=entity,
        limit=limit,
        reverse=reverse,
    )

    if only_unique_docs:
        messages = await OnlyUniqueDocs().filter(
            filter(MessageDownloadable.guard, messages)
        )

    for m in messages:
        classes = classifier.classify_str(m)

        if factory.supports(m):
            if only_unsupported:
                continue

            types_str = (
                ",".join(classes)
                if print_all_matching_types
                else factory.get_cls(m).__name__
            )

            original_fname = (
                f"\t{m.file.name}"
                if m.file is not None and m.file.name is not None
                else ""
            )

            document_id = (
                MessageDownloadable.document_or_photo_id(m)
                if MessageDownloadable.guard(m)
                else "<not a document>"
            )

            # if print_sender:
            #     sender = await m.get_sender()
            #     print(sender.username)

            print(
                f"{m.id}\t{document_id}\t{types_str}\t{factory.size(m)}\t{await factory.filename(m)}{original_fname}"
            )

            if print_message_object:
                print(m)

        elif include_unsupported or only_unsupported:
            if m.media is None and m.document is None and m.file is None:
                continue

            print(
                f"{m.id}\tfile={m.file}, document={m.document}, media={m.media} unsupported"
            )

            if print_message_object:
                print(m)


def add_list_documents_arguments(command_list_documents: ArgumentParser):
    command_list_documents.add_argument("entity", type=util.int_or_string)
    command_list_documents.add_argument("--limit", type=int, required=False)
    command_list_documents.add_argument("--reverse", action="store_true", default=False)
    command_list_documents.add_argument(
        "--print-message",
        "-p",
        dest="print_message_object",
        action="store_true",
        default=False,
        help="Print message object",
    )
    command_list_documents.add_argument(
        "--include-unsupported",
        "-u",
        dest="include_unsupported",
        action="store_true",
        default=False,
        help="Include messages that are unsupported for mounting",
    )

    command_list_documents.add_argument(
        "--only-unsupported",
        "-U",
        dest="only_unsupported",
        action="store_true",
        default=False,
        help="Only print messages that are unsupported for mounting",
    )

    command_list_documents.add_argument(
        "--all-types",
        "-t",
        dest="print_all_matching_types",
        action="store_true",
        default=False,
        help="Print all matching message types",
    )

    command_list_documents.add_argument(
        "--only-unique-docs",
        "-q",
        dest="only_unique_docs",
        action="store_true",
        default=False,
        help="Exclude duplicate documents",
    )
