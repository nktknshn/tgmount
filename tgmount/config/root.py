from .helpers import *
from dataclasses import dataclass

@dataclass
class ContentDir:
    filter: Union[str, list[str]]
    cache: Optional[str] = None

    def get_filters(self) -> list[str]:
        if isinstance(self.filter, list):
            return self.filter

        return [self.filter]

    @staticmethod
    def from_dict(d: dict) -> "ContentDir":
        return load_class_from_dict(ContentDir, d)


ContentDirs = ContentDir | dict[str, "ContentDirs"]


@dataclass
class Content:
    source: str
    dirs: Optional[ContentDirs] = None
    filter: Optional[Union[str, list[str]]] = None
    cache: Optional[str] = None

    def get_filters(self) -> Optional[list[str]]:
        if self.filter is None:
            return None

        if isinstance(self.filter, list):
            return self.filter

        return [self.filter]

    def get_dirs_list(self) -> Optional[list[ContentDir]]:
        if self.dirs is None:
            return None

        return fold_tree(lambda v, res: [*res, v], self.dirs, [])

    @staticmethod
    def dirs_from_dict(d: dict) -> "ContentDirs":
        filter = d.get("filter")

        if filter is None:
            return {k: Content.dirs_from_dict(v) for k, v in d.items()}

        return ContentDir.from_dict(d)

    @staticmethod
    def from_dict(d: dict) -> "Content":

        return load_class_from_dict(
            Content,
            d,
            loaders={
                "dirs": lambda d: Content.dirs_from_dict(d["dirs"])
                if "dirs" in d
                else None
            },
        )


RootTree = Content | Mapping[str, "RootTree"]


@dataclass
class Root:
    content: dict

    @staticmethod
    def from_dict(d: dict) -> "Root":
        return Root(d)


@dataclass
class Root2:
    content: RootTree

    def get_filters_set(self) -> set[str]:
        contents = self.get_contents_list()
        content_dirs = self.get_content_dirs_list()

        return set(
            col.flatten(
                [
                    *map(lambda a: a.get_filters(), content_dirs),
                    *filter(bool, map(lambda a: a.get_filters(), contents)),
                ]
            ),
        )

    def get_contents_list(self) -> list[Content]:
        return fold_tree(lambda v, res: [*res, v], self.content, [])

    def get_content_dirs_list(self) -> list[ContentDir]:
        contents = self.get_contents_list()
        return col.flatten(
            filter(
                bool,
                map(lambda c: c.get_dirs_list(), contents),
            )
        )

    @staticmethod
    def from_dict(d: dict) -> "Root2":
        return load_class_from_dict(
            Root2, d, loaders={"content": Root2.root_tree_from_dict}
        )

    @staticmethod
    def root_tree_from_dict(d: dict) -> RootTree:
        source = d.get("source")

        if source is None:
            return {k: Root2.root_tree_from_dict(v) for k, v in d.items()}

        return Content.from_dict(d)
