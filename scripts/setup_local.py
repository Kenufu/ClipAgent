"""Explicit first-run setup. Runtime inference never downloads a missing model."""
import os
from faster_whisper import WhisperModel
from clipagent.config import MODELS


def main():
    model = os.environ.get('CLIPAGENT_WHISPER_MODEL', 'tiny.en')
    settings = dict(device='cpu', compute_type='int8', download_root=str(MODELS))
    print(f'准备语音模型 {model}（CPU，无需显卡）…', flush=True)
    try:
        WhisperModel(model, local_files_only=True, **settings)
        print('使用已缓存模型。')
    except Exception:
        print('本地模型尚不可用，开始联网获取；网络中断后可重新运行安装。', flush=True)
        WhisperModel(model, **settings)
    from scripts import prepare_samples  # copies the bundled examples if missing
    print('模型和演示素材已就绪。')


if __name__ == '__main__':
    main()
