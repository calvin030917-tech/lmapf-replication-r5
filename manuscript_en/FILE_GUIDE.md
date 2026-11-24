# `manuscript_en/` 文件说明 / File guide

[上一级文件索引 / Parent file guide](../FILE_GUIDE.md)

| 文件或目录 / File or folder | 中文说明 | English description |
| --- | --- | --- |
| [`paper_en.txt`](paper_en.txt) | 英文正文源，含章节、图表和参考文献的插入标记。 | English manuscript source with section, figure, table, and bibliography markers. |
| [`aligned_tables.py`](aligned_tables.py) | 组织英文表格的列名、内容及说明，使其与中文稿的数据一致。 | Aligns English table columns, contents, and notes with the data used by the Chinese manuscript. |
| [`build_aligned_tex.py`](build_aligned_tex.py) | 从英文正文和对齐表格生成匿名投稿稿件的 LaTeX 主文件。 | Generates the anonymous submission LaTeX source from English text and aligned tables. |
| [`build_aligned_word.py`](build_aligned_word.py) | 按与中文稿一致的图表和章节顺序构建英文 Word 稿。 | Builds the English Word draft in the same section and display order as the Chinese version. |
| [`render_data.py`](render_data.py) | 把实验汇总转成可插入 LaTeX 的表格行和数值片段。 | Converts experiment summaries into LaTeX table rows and numerical snippets. |
| [`lmapf_r5.tex`](lmapf_r5.tex) | 已经生成的英文匿名投稿主 TeX，供论文排版工具编译。 | Generated main TeX source for typesetting the anonymous English submission. |
| [`references.bib`](references.bib) | 供 BibTeX 使用的英文论文参考文献数据库。 | BibTeX bibliography database for the English manuscript. |
| [`generated_cells.tex`](generated_cells.tex) | 公开地图各分层的配对数、事件数、完成情况和共享边结果行。 | Public-map stratum rows with pair counts, events, completion, and shared-edge results. |
| [`generated_mechanisms.tex`](generated_mechanisms.tex) | 四种局部机制的阳性、误报和漏报列。 | Positive, false-positive, and false-negative columns for four local mechanisms. |
| [`generated_policy.tex`](generated_policy.tex) | 不同场景下策略对比效应和区间的 LaTeX 表格行。 | LaTeX table rows of policy effects and intervals by setting. |
| [`generated_proxy.tex`](generated_proxy.tex) | 首步方向与两步推进代理判据的混淆统计。 | Confusion counts for the first-step direction and two-step progress proxies. |
| [`generated_values.tex`](generated_values.tex) | 由数据导出脚本生成的汇总数值宏，可供 LaTeX 排版引用。 | Summary value macros exported by the data renderer for potential LaTeX use. |
| [`generated_workload.tex`](generated_workload.tex) | 分场景的规划时间分位数与中位操作计数。 | Scenario planning-time percentiles and median operation counts. |
| [`algorithm.sty`](algorithm.sty) | 为 LaTeX 提供算法浮动体和标题环境。 | Provides algorithm floats and captions in LaTeX. |
| [`algorithmic.sty`](algorithmic.sty) | 为 LaTeX 提供算法伪代码排版环境。 | Provides the algorithmic pseudocode environment in LaTeX. |
| [`fancyhdr.sty`](fancyhdr.sty) | 设置 LaTeX 页眉和页脚的样式依赖。 | Page-header and footer formatting dependency for LaTeX. |
| [`icml2027.sty`](icml2027.sty) | 匿名英文投稿稿件使用的 ICML 2027 版式样式。 | ICML 2027 document style used by the anonymous English submission. |
| [`icml2027.bst`](icml2027.bst) | 英文投稿稿引用的 ICML 2027 BibTeX 排版样式。 | ICML 2027 BibTeX bibliography style used by the English submission. |
| [`figures/`](figures/FILE_GUIDE.md) | 英文 LaTeX 稿所用两幅图的归档副本。 | Archived copies of the two figures used by the English LaTeX manuscript. |
