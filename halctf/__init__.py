"""HalCTF 自律ペンテストエージェント harness。

層構成（ブリーフ §3）:
  - halctf.client : 中央 Model Service への OpenAI 互換クライアント（モデル多段切替）
  - halctf.tools  : recon / exploit / flag_submit などエージェントの道具
  - halctf.loop   : ReAct 系の自律決定ループ（小型モデル最適化）
  - halctf.submit : フラグ提出 / 完了通知 API の抽象化
"""

__version__ = "0.1.0"
