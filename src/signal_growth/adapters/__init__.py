"""Provider adapters for deterministic, credential-free connector workflows."""

from .base import BaseChannelAdapter, ChannelAdapter, InjectedTransport
from .channel_talk import ChannelTalkAdapter
from .naver_talktalk import NaverTalkTalkAdapter

__all__ = [
    "BaseChannelAdapter",
    "ChannelAdapter",
    "ChannelTalkAdapter",
    "InjectedTransport",
    "NaverTalkTalkAdapter",
]
