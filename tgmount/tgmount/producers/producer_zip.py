from typing import Mapping, Sequence
from zipfile import BadZipFile
from tgmount import vfs
from tgmount.tgclient.guards import MessageDownloadable
from tgmount.tgclient.message_types import MessageProto
from tgmount.tgclient.messages_collection import MessagesCollection
from tgmount.tgmount.producers.producer_plain import VfsTreeProducerPlainDir
from tgmount.tgmount.vfs_tree_producer_types import (
    VfsTreeProducerConfig,
    VfsTreeProducerProto,
)
from tgmount.tgmount.wrappers.wrapper_zips_as_dirs import WrapperZipsAsDirsProps
from tgmount.util import yes
from .logger import module_logger as _logger
from tgmount.tgmount.vfs_tree import VfsTreeDir
from tgmount import zip as z


class VfsProducerZip(VfsTreeProducerPlainDir):
    logger = _logger.getChild("VfsProducerZip")

    def __init__(
        self,
        tree_dir: VfsTreeDir,
        vfs_config: VfsTreeProducerConfig,
        props: WrapperZipsAsDirsProps,
    ) -> None:
        super().__init__(tree_dir, vfs_config)
        # self._tree_dir = tree_dir
        # self._config = vfs_config
        self._props = props

        self._dir_content_zip_factory = z.DirContentZipFactory.create_from_props(
            fix_Id3v1=props.fix_id3v1
        )

        self._logger = self.logger.getChild(
            f"{self._tree_dir.path}", suffix_as_tag=True
        )

        self._zip_to_dirlike: dict[str, vfs.DirLike] = {}

    async def update_items_in_vfs_tree(
        self,
        old_files: Mapping[str, tuple[MessageProto, vfs.FileLike]],
        new_files: Mapping[str, tuple[MessageProto, vfs.FileLike]],
        update_content_dict: Mapping[str, vfs.FileLike],
    ):
        result = {}

        for old_file_name, new_file in update_content_dict.items():
            (old_msg, old_file) = old_files[old_file_name]
            (new_msg, new_file) = new_files[new_file.name]

            is_old_zip = await self._is_zip_file(old_file)
            is_new_zip = await self._is_zip_file(new_file)

            name_changed = old_file_name != new_file.name

            if not is_old_zip and not is_new_zip:
                result[old_file_name] = new_file
                continue

            if is_old_zip and is_new_zip:
                # in case both old and new file were zips
                old_doc_id = MessageDownloadable.document_or_photo_id(old_msg)
                new_doc_id = MessageDownloadable.document_or_photo_id(new_msg)

                if old_doc_id == new_doc_id:
                    # reactions or text changed, not document
                    result[old_file_name] = new_file
                    continue

            await self.remove_items_from_vfs_dir([old_file])
            await self.add_items_to_vfs_tree([new_file])

        await self._tree_dir.update_content(result)

    async def add_items_to_vfs_tree(self, items: Sequence[vfs.DirContentItem]):
        result = []

        for item in items:
            if isinstance(item, vfs.DirLike):
                result.append(item)

            elif await self._is_zip_file(item):
                self._logger.debug(f"Adding zip file {item.name}")

                dirlike = await self._add_zip_file(item)

                if yes(dirlike):
                    result.append(dirlike)

                    if not self._props.hide_zip_files:
                        result.append(item)
                else:
                    result.append(item)
            else:
                result.append(item)

        return await super().add_items_to_vfs_tree(result)

    async def _add_zip_file(self, zip_file: vfs.FileLike):
        try:

            zip_tree = await self._dir_content_zip_factory.get_ziptree(zip_file.content)
        except BadZipFile:
            self._logger.warning(f"{zip_file} is a bad zip file")
            return

        zip_tree_root_items_names = list(
            set(zip_tree.keys()).difference(
                self._props.skip_single_root_subfolder_exclude_from_root
            )
        )

        zip_tree_root_items = list(zip_tree[k] for k in zip_tree_root_items_names)

        root_item = zip_tree_root_items[0]

        if (
            self._props.skip_single_root_subfolder
            and isinstance(root_item, dict)
            and len(zip_tree_root_items) == 1
        ):
            # handle skip_single_root_subfolder props
            if isinstance(zip_file.extra, tuple):
                # if there is a source message info in the extra
                message_id = zip_file.extra[0]
                zip_dir_name = f"{message_id}_{zip_tree_root_items_names[0]}"
            else:
                zip_dir_name = zip_tree_root_items_names[0]

            zip_dir_content = (
                await self._dir_content_zip_factory.create_dir_content_from_ziptree(
                    zip_file.content,
                    root_item,
                )
            )
        else:
            zip_dir_name = self._props.dir_name_mapper(zip_file)
            zip_dir_content = (
                await self._dir_content_zip_factory.create_dir_content_from_ziptree(
                    zip_file.content, zip_tree
                )
            )

        dirlike = self._zip_to_dirlike[zip_file.name] = vfs.DirLike(
            zip_dir_name, zip_dir_content, extra=zip_file.extra
        )

        return dirlike

    async def remove_items_from_vfs_dir(self, items: Sequence[vfs.FileLike]):
        result = []
        for item in items:
            if item.name in self._zip_to_dirlike:
                dirlike = self._zip_to_dirlike[item.name]
                del self._zip_to_dirlike[item.name]

                result.append(dirlike)

                if not self._props.hide_zip_files:
                    result.append(item)
            else:
                result.append(item)

        return await super().remove_items_from_vfs_dir(result)

    async def _is_zip_file(self, zip_file_like: vfs.FileLike):
        return zip_file_like.name.endswith(".zip")

    @classmethod
    async def from_config(
        cls,
        resources,
        vfs_config: VfsTreeProducerConfig,
        config: Mapping,
        tree_dir: VfsTreeDir,
    ):

        return VfsProducerZip(
            tree_dir, vfs_config, props=WrapperZipsAsDirsProps.from_config(config)
        )
