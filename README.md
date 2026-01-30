# Simple Collada DAE Exporter for Blender

A simple Collada DAE format exporter plugin for Blender 5.0+, for Blender  stops supporting Collada DAE import-export since Blender 5.0.                                           

## Features

- Export mesh objects to Collada DAE 1.4.1 format
- Support for materials and texture maps
- Support for vertex normals and UV coordinates
- Automatic triangulation of polygons
- Apply modifiers before export
- World coordinate system baking for vertex positions

## Installation

1. Open Blender
2. Edit > Preferences > Add-ons > Install from disk
3. Select the `simpleDAEExporter.py` file
4. Enable the plugin

## Usage

1. Select mesh objects to export
2. File > Export > Collada DAE (.dae)
3. Configure export options and export

## Export Options

| Option | Description | Default |
|--------|-------------|---------|
| Selection Only | Export selected objects only | Enabled |
| Apply Modifiers | Apply modifiers before exporting | Enabled |
| Export Materials | Export materials and textures | Enabled |
| Export Normals | Export vertex normals | Enabled |
| Export UVs | Export texture coordinates | Enabled |
| Triangulate | Convert all faces to triangles | Enabled |

## Supported Features

- **Materials**: Principled BSDF base color support
- **Textures**: Image texture nodes support (relative paths)
- **Coordinate System**: Z-up (consistent with Blender)
- **Units**: Meters

## Known Issues

1. When exporting multi-material object, only the material in the first slot will be exported.
2. Using native python without numpy, when exporting complex mesh, it may be very slow or crashed. Avoid exporting complex mesh(es) at one time.

---

# Blender 5.0+ 的 Collada DAE 导出器

Blender从5.0版本开始停止支持collada dae格式。这是Blender 5.0+ 的简单 Collada DAE 格式导出插件，以供有需者使用。目前功能有限，仅够我自用。

## 功能特点

- 导出网格物体为 Collada DAE 1.4.1 格式
- 支持导出材质和纹理贴图
- 支持导出顶点法线和 UV 坐标
- 自动三角化多边形
- 应用修改器后导出
- 使用世界坐标系烘焙顶点位置

## 安装方法

1. 打开 Blender
2. 编辑 > 偏好设置 > 插件 > 从磁盘安装
3. 选择 `simpleDAEExporter.py` 文件
4. 勾选启用插件

## 使用方法

1. 选择要导出的网格物体
2. 文件 > 导出 > Collada DAE (.dae)
3. 设置导出选项并导出

## 导出选项

| 选项 | 说明 | 默认值 |
|------|------|--------|
| Selection Only | 仅导出选中物体 | 开启 |
| Apply Modifiers | 应用修改器后导出 | 开启 |
| Export Materials | 导出材质和纹理 | 开启 |
| Export Normals | 导出顶点法线 | 开启 |
| Export UVs | 导出 UV 坐标 | 开启 |
| Triangulate | 自动三角化 | 开启 |

## 支持特性

- **材质**: 支持 Principled BSDF 的基础颜色
- **纹理**: 支持图像纹理节点（相对路径）
- **坐标系**: Z-up (与 Blender 一致)
- **单位**: 米

## 已知问题

1. 当导出多材质网格时，只导出第一个材质槽的材质。
2. 使用原生 Python 而非 numpy ，当导出复杂网格时，可能会非常慢或崩溃，建议每次只导出少量简单物体，避免面数过多。
