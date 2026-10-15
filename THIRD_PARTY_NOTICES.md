# 第三方组件说明

安装包内置 `sherpa-onnx-streaming-paraformer-bilingual-zh-en` 的 `tokens.txt`、`encoder.int8.onnx` 和 `decoder.int8.onnx`，供本机语音识别使用。模型来源见 [sherpa-onnx 的模型文档](https://github.com/k2-fsa/sherpa/blob/master/docs/source/onnx/pretrained_models/online-paraformer/paraformer-models.rst)；模型发布页面注明 Apache License 2.0，许可证全文随安装包保存在 `licenses/LICENSE-APACHE-2.0.txt`。

程序还依赖 PyQt6、sherpa-onnx、PyAudioWPatch、PyMuPDF、NumPy 等第三方库。各组件保留其原有许可证；本项目的 MIT 许可证仅适用于本项目及原项目相应代码，不替代第三方许可证。
