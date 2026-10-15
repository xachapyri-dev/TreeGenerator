<p align="center">
  <img src="https://github.com/user-attachments/assets/22602a34-a3c0-4145-8d99-be9d845a801d" alt="Tree Generator Icon" width="96" height="96">
</p>

<p align="center">
  <img src="https://github.com/user-attachments/assets/b06111ce-f067-4a25-b7dd-de6a12bba8f8" alt="Tree Generator Banner" width="100%">
</p>

<h1 align="center">Tree Generator</h1>

<p align="center">
  Кроссплатформенный процедурный генератор 3D-деревьев с аппаратным вьювером OpenGL 3.3 Core, ручным текстурированием и автоматизированным экспортом готовых префабов для Unity и форматов 3D-моделирования.
</p>

<p align="center">
  <a href="https://xachapyri-dev.itch.io/tree-generator">
    <img src="https://img.shields.io/badge/itch.io-Скачать%20на%20Itch.io-FA5C5C?style=for-the-badge&logo=itchdotio&logoColor=white" alt="Itch.io Page">
  </a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.13">
  <img src="https://img.shields.io/badge/Platforms-Windows%20%7C%20Linux-0078D6?style=flat-square" alt="Platforms">
  <img src="https://img.shields.io/badge/GUI-PyQt6%20%7C%20PySide6-41CD52?style=flat-square&logo=qt&logoColor=white" alt="Qt">
  <img src="https://img.shields.io/badge/Graphics-OpenGL%203.3%20Core-5586A4?style=flat-square&logo=opengl&logoColor=white" alt="OpenGL">
  <img src="https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-2088FF?style=flat-square&logo=githubactions&logoColor=white" alt="GitHub Actions">
  <img src="https://img.shields.io/badge/Format-.tgtree%20%28ZIP%29-orange?style=flat-square" alt="Format">
</p>

---

## Описание

**Tree Generator** — легковесное десктопное приложение для быстрой процедурной генерации низко- и среднеполигональных моделей деревьев. Программа ориентирована на независимых разработчиков игр и 3D-художников, предоставляя возможность настраивать анатомию дерева в реальном времени, подключать пользовательские PBR-текстуры и экспортировать геометрию с готовыми материалами и префабами без необходимости ручной сборки в движке.

Релизы и сборки под Windows доступны на [официальной странице Itch.io](https://xachapyri-dev.itch.io/tree-generator). Сборка пакетов под Linux автоматизирована через GitHub Actions.

---

## Функциональные возможности

### Процедурная генерация и морфология
* **Филлотаксис на основе Золотого угла:** распределение ветвей вдоль ствола опирается на Золотой угол (~137.508°), что исключает пустоты и скопление веток на одной стороне кроны.
* **Анатомическая структура:** реалистичный расчет сбежистости ствола, клёш прикорневой шейки (buttress roots) и верхушечная развилка, закрывающаяся куполом листвы без торчащего голого шпиля.
* **Гравитация и тропизм:** ветви нижнего яруса плавно прогибаются под собственным весом, в то время как верхушечные побеги направлены вверх к свету.
* **Недеструктивное редактирование:** кнопка «Генерировать» создает новое уникальное дерево со своим случайным сидом, а ползунки параметров (высота, плотность ствола, количество основных и боковых веток, число листьев) модифицируют текущую геометрию на лету без сброса композиции.

### Текстурирование и Leaf Editor
* **Пользовательские текстуры:** текстурные карты подбираются и подключаются пользователем вручную отдельно для ствола и листвы.
* **Поддерживаемые слоты:** Albedo / Diffuse, Normal Map, Roughness, Transmission (светопропускание листьев), Ambient Occlusion (AO).
* **Интерактивный Leaf Editor:** мини-редактор для указания точки привязки черешка на загруженной текстуре листа, что гарантирует правильную ориентацию листовых карточек относительно веток.

### PBR-рендеринг и формат проектов
* **OpenGL 3.3 Core Profile:** аппаратный предпросмотр в реальном времени с поддержкой карт нормалей, шероховатости, окклюзии и сферических нормалей кроны (Bent Normals).
* **Собственный формат `.tgtree`:** проект упаковывается в переносимый ZIP-архив, включающий JSON-конфигурацию, сериализованную геометрию (`.npz`) и локальные копии текстур.
* **История правок:** полная поддержка отмены и повтора действий (`Ctrl + Z` / `Ctrl + Y`), быстрое сохранение (`Ctrl + S`) и предупреждение о несохраненных данных при закрытии.

---

## Поддерживаемые форматы экспорта

| Целевая платформа | Файлы экспорта | Технические особенности |
| :--- | :--- | :--- |
| **Unity Built-in** | `Trunk.obj`, `Leaf.obj`, `Trunk.mat`, `Leaf.mat`, `Tree_Model.prefab` | Шейдеры `Nature/Tree Creator`, жесткая привязка мешей через `fileID: 4300000`, связанные `.meta`-файлы. |
| **Unity URP** | `Trunk.obj`, `Leaf.obj`, `Trunk.mat`, `Leaf.mat`, `Tree_Model.prefab` | Шейдер `Universal Render Pipeline/Lit`, автоматическая сборка карты `MetallicSmoothness` (R=0, A=1-Roughness), Alpha Clipping (`2450`) и двусторонний рендер (`_Cull: 0`). |
| **Unity HDRP** | `Trunk.obj`, `Leaf.obj`, `Trunk.mat`, `Leaf.mat`, `Tree_Model.prefab` | Шейдер `HDRP/Lit`, автоматический синтез текстуры `MaskMap` (R=Metallic, G=AO, B=Detail, A=Smoothness), активация `Transmission` и `ThicknessMap`. |
| **GLB (glTF 2.0)** | Единый файл `.glb` | Бинарный контейнер со встроенными буферами сетки, PBR-параметрами и запакованными текстурами. Подходит для Godot, Blender, Three.js. |
| **OBJ** | `Trunk.obj`, `Leaf.obj`, `*.mtl` | Классический формат с разбиением на группы материалов для любых 3D-пакетов. |
| **FBX** | `Tree_Model.fbx` | Стандартный формат обмена геометрии. |

---

## Управление во вьювере

* **Левая кнопка мыши (ЛКМ) + перемещение:** вращение камеры вокруг дерева.
* **Правая кнопка мыши (ПКМ) + перемещение:** вертикальное перемещение фокуса по высоте ствола.
* **Колесико мыши:** масштабирование (зум).
* **Ctrl + Z:** отмена последнего действия.
* **Ctrl + Y / Ctrl + Shift + Z:** повтор отмененного действия.
* **Ctrl + S:** быстрое сохранение в текущий `.tgtree` проект.

---

## Локализация интерфейса

* **Русский язык:** [x] Полный перевод (100%)
* **Английский язык (English):** [ ] Завершено на ~95%

---

## Установка и запуск

### Требования
* Python 3.13
* Графический адаптер с поддержкой OpenGL 3.3 Core Profile

### Установка зависимостей

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/xachapyri-dev/TreeGenerator.git
   cd TreeGenerator
   ```
2. Установите зависимости:

    * Только запуск приложения:
   
   ```
    pip install -r requirements.txt
   ```
   * Для разработки и сборки:
   
   ```
    pip install -r requirements-dev.txt
   ```
3. Запустите приложение:
   ```
   python main.py
   ```

## Сборка дистрибутивов

### Сборка под Windows

Для сборки под Windows можно использовать ``auto-py-to-exe`` или запустить PyInstaller вручную:
```
pyinstaller main.py --name TreeGenerator --onedir --windowed --noconfirm --clean --icon favicon.ico --hidden-import OpenGL.arrays.numpymodule --hidden-import OpenGL.arrays.ctypesarrays --hidden-import pyrr
```
После сборки скопируйте папки `shaders/`, `translation/` и файл `favicon.png` в корень созданного каталога `dist/TreeGenerator/`.

### Сборка под Linux (CI/CD)

Сборка под Linux выполняется автоматически в GitHub Actions через воркфлоу `.github/workflows/build-linux.yml`. Готовый исполняемый пакет с папкой `_internal` и ресурсами упаковывается в архив `TreeGenerator-Linux.tar.gz` и публикуется в артефактах сборки.

> [!WARNING]
> Отказ от ответственности <br>
>
> Программное обеспечение предоставляется на условиях «КАК ЕСТЬ» («AS IS»), без каких-либо явных или подразумеваемых гарантий, включая, но не ограничиваясь, гарантиями коммерческой пригодности, соответствия конкретным целям или отсутствия нарушений. <br>
>
> Автор и разработчики ни при каких обстоятельствах не несут ответственности за любые прямые, косвенные, случайные или штрафные убытки, сбои в работе оборудования, потерю данных или несовместимость с конкретными версиями сторонних движков (включая обновления версий Unity, графических драйверов или операционных систем), возникшие вследствие использования или невозможности использования данного программного обеспечения. Вы используете приложение исключительно на свой страх и риск.

> [!TIP]
> Проект бесплатный. Буду рад отзывам и замечаниям ^_^ <br>
> плюс если будут проблемы с работой приложения, то пишите в [issues](https://github.com/xachapyri-dev/TreeGenerator/issues)
