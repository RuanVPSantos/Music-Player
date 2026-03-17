"""Data models for the player application."""

from dataclasses import dataclass


@dataclass
class Music:
    id: str
    title: str
    url: str
    duration: int
    thumbnail: str
    file_path: str


@dataclass
class Playlist:
    id: str
    name: str


@dataclass
class Tag:
    id: str
    name: str


@dataclass
class SyncPlaylist:
    id: str
    name: str
    url: str
