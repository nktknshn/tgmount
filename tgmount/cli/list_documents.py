from argparse import ArgumentParser
from typing import Optional

from telethon import hints
from tgmount.tgmount.file_factory import FileFactoryDefault

from tgmount import tgclient
from tgmount import util
from tgmount.tgclient import TgmountTelegramClient
from tgmount.tgclient.guards import MessageDownloadable
from tgmount.tgmount.filters import OnlyUniqueDocs


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
):
    factory = FileFactoryDefault(
        files_source=tgclient.TelegramFilesSource(client), extra_files_source={}
    )

    messages = await client.get_messages_typed(
        entity=entity,
        limit=limit,
        reverse=reverse,
    )

    if only_unique_docs:
        messages = await OnlyUniqueDocs().filter(
            filter(MessageDownloadable.guard, messages)
        )

    for m in messages:
        if factory.supports(m):
            if only_unsupported:
                continue

            types_str = (
                ",".join(factory.message_types(m))
                if print_all_matching_types
                else factory.message_type(m)
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

            print(
                f"{m.id}\t{document_id}\t{types_str}\t{factory.size(m)}\t{factory.filename(m)}{original_fname}"
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
