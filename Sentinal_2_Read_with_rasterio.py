import rasterio
import numpy as np
import os
import xml.etree.ElementTree as ET
from rasterio.warp import Resampling
from rasterio.enums import ColorInterp
from osgeo import gdal
import zipfile


# 读取Sentinel-2A的数据文件，查找元数据，获取左上角坐标和分辨率
def get_coords_res(product_uri_archive: str) -> (str, dict[dict]):
    """读取Sentinel-2A的数据文件，查找元数据，获取左上角坐标和分辨率
    Args:
        product_uri_archive (_type_): 文件路径
    Returns:
        str, dict[dict]: 投影参数EPSG，图像左上角坐标和分辨率
    """
    with zipfile.ZipFile(product_uri_archive, 'r') as myzip:
        # 检查MTD_TL.xml是否在ZIP文件中
        if any (file.endswith('MTD_TL.xml') for file in myzip.namelist()):
            # 从ZIP文件中读取MTD_TL.xml
            file = [file for file in myzip.namelist() if file.endswith('MTD_TL.xml')][0]
            with myzip.open(file) as f:
                # 解析XML文件
                tree = ET.parse(f)
                root = tree.getroot()
                # 获取投影参数EPSG
                crs_value = root.find('.//HORIZONTAL_CS_CODE').text
                coords_res = {
                    'resolution_10m': [],
                    'resolution_20m': [],
                    'resolution_60m': []
                }
                for geoposition in root.iter("Geoposition"):
                    # 检查 resolution 属性是否为 "10", "20" 或 "60"
                    resolution = geoposition.get('resolution')
                    if resolution in ['10', '20', '60']:
                        # 获取左上角坐标和分辨率
                        ulx = float(geoposition.find('ULX').text)
                        uly = float(geoposition.find('ULY').text)
                        xdim = float(geoposition.find('XDIM').text)
                        ydim = float(geoposition.find('YDIM').text)
                        # 将左上角坐标和分辨率存储在字典中
                        coords_res["resolution_" + resolution + "m"].append({
                            'ulx': ulx,
                            'uly': uly,
                            'xdim': xdim,
                            'ydim': ydim
                        })
            return crs_value, coords_res
        else:
            raise Exception("MTD_TL.xml not found in ZIP file")

# 读取Sentinel-2A的元数据文件，获取每个波段的波长信息
def get_wavelength(product_uri_archive: str, physical_bands: list) -> dict[dict]:
    """
    在指定的Sentinel-2A数据路径中查找MTD_MSIL2A.xml文件，解析XML文件并返回波段和对应的波长信息。
    Args:
        product_uri_archive (str): Sentinel-2A数据的路径
        physical_bands (list): 物理波段列表"""
    with zipfile.ZipFile(product_uri_archive, 'r') as myzip:
        for filename in myzip.namelist():
            if filename.endswith('MTD_MSIL2A.xml'):
                with myzip.open(filename) as f:
                    tree = ET.parse(f)
                    root = tree.getroot()
                    # 创建一个字典来存储波段和对应的波长信息
                    band_wavelengths = {}
                    # 遍历XML文件中的所有'Spectral_Information'节点
                    for spectral_info in root.iter('Spectral_Information'):
                        # 获取波段名
                        band_name = spectral_info.get('physicalBand')
                        # 如果波段名在我们的列表中
                        if band_name in physical_bands:
                            # 获取波长信息
                            wavelength = spectral_info.find('Wavelength')
                            min_wavelength = wavelength.find('MIN').text
                            max_wavelength = wavelength.find('MAX').text
                            central_wavelength = wavelength.find('CENTRAL').text
                            # 将波段名和波长信息添加到字典中
                            band_wavelengths[band_name] = {
                                'minValue': min_wavelength,
                                'maxValue': max_wavelength,
                                'centralValue': central_wavelength
                            }
                    break
    return band_wavelengths

# 读取产品的载荷平台名称
def get_spacecraft_name(product_uri_archive: str) -> str:
    """
    在指定的Sentinel-2A数据路径中查找MTD_MSIL2A.xml文件，解析XML文件并返回载荷平台名称
    Args:
        product_uri_archive (str): Sentinel-2A数据的路径"""
    with zipfile.ZipFile(product_uri_archive, 'r') as myzip:
        for filename in myzip.namelist():
            if filename.endswith('MTD_MSIL2A.xml'):
                with myzip.open(filename) as f:
                    tree = ET.parse(f)
                    root = tree.getroot()
                    # 在已经解析的XML树中查找'SPACECRAFT_NAME'标签
                    spacecraft_name_elements = root.iter('SPACECRAFT_NAME')
                    # 获取'SPACECRAFT_NAME'的值
                    if spacecraft_name_elements is not None:
                        for spacecraft_name_element in spacecraft_name_elements:
                            spacecraft_name = spacecraft_name_element.text
                            print(f"Spacecraft name: {spacecraft_name}")
                    else:
                        spacecraft_name = 'Unknown'
                        print("'SPACECRAFT_NAME' tag not found in the XML file.")
    return spacecraft_name
                    
def rasterio_zipfile_path(zip_path: str) -> str:
    """将zip文件路径转换为rasterio的zip文件路径格式
    Args:
        zip_path (str): zip文件的完整路径名称
    Returns:
        str: 符合rasterio的zip文件路径格式
    """
    return f"zip:{zip_path}!"

def gdal_zipfile_path(zip_path: str) -> str:
    """将zip文件路径转换为gdal的zip文件路径格式
    Args:
        zip_path (str): zip文件的完整路径名称
    Returns:
        str: 符合gdal的zip文件路径格式
    """
    return f"/vsizip/{zip_path}"

# 对每个需要重采样的文件进行重采样
def resample_data (file: str) -> tuple[np.ndarray, rasterio.Affine]:
    """_summary_

    Args:
        file (str): _description_

    Returns:
        tuple[np.ndarray, rasterio.Affine]: _description_
    """
    with rasterio.open(file) as src:
        # 创建一个新的变换
        left, bottom, right, top = src.bounds.left, src.bounds.bottom, src.bounds.right, src.bounds.top
        # print(f'"left:{left}, bottom:{bottom}, right:{right}, top:{top}"')
        ulx=left
        uly=top        
        xdim = 10
        ydim = 10
        new_transform = rasterio.Affine.translation(ulx, uly) * rasterio.Affine.scale(xdim, -ydim)
        # 重采样数据到新的分辨率
        data = src.read(
            out_shape=(src.count, max_height, max_width),
            resampling=Resampling.bilinear
        )

        return data, new_transform

# 对不需要重采样的波段也进行重采样
def no_resample_data(file) -> tuple[np.ndarray, rasterio.Affine]:
    with rasterio.open(file) as src:
        left, bottom, right, top = src.bounds.left, src.bounds.bottom, src.bounds.right, src.bounds.top
        # print(f'"left:{left}, bottom:{bottom}, right:{right}, top:{top}"')
        ulx=left
        uly=top        
        xdim = 10
        ydim = 10
        new_transform = rasterio.Affine.translation(ulx, uly) * rasterio.Affine.scale(xdim, -ydim)

        # 重采样数据到新的分辨率
        data = src.read(
            out_shape=(src.count, max_height, max_width),
            resampling=Resampling.bilinear
        )
        return data, new_transform

def modify_hdr_file(work_path, merged_product_uri_file_hdr, band_wavelengths, wavelength_unit):
    """
    修改hdr文件
    Args:
        work_path (str): 工作路径
        merged_product_uri_file_hdr (str): hdr文件名称
        band_wavelengths (dict): 波段和波长信息
        wavelength_unit (str): 波长单位
    """
    # 获取字典中每个band的centralValue
    central_values = [str(band['centralValue']) for band in band_wavelengths.values()]
    # 将centralValue的值连接成一个字符串
    my_string = ', '.join(central_values)

    with open(os.path.join(work_path, merged_product_uri_file_hdr), 'a') as f:
        f.write(f"wavelength units = {wavelength_unit}\n")
        f.write(f"wavelength = {{{my_string}}}\n")

        

if __name__ == '__main__':
    # Sentinel-2 数据的路径
    product_uri = 'S2A_MSIL2A_20210826T073611_N9999_R092_T37QGF_20230417T124934.SAFE'
    work_path = r"D:\遥感数据"
    merged_product_uri_file = product_uri+"_band_stacks.tif"
    product_uri_file = product_uri+".zip"
    merged_product_uri_file_hdr = product_uri+"_band_stacks.hdr"
    product_uri_archive=os.path.join(work_path, product_uri_file)

    # 在 Sentinel-2 数据中找到所有的.jp2 文件
    with zipfile.ZipFile(product_uri_archive, 'r') as myzip:
        # 使用列表推导式来获取所有.jp2文件
        jp2_files = [filename for filename in myzip.namelist() if filename.endswith('.jp2')]

    # 挑选需要重采样的波段，例如 B02（蓝色波段）、B03（绿色波段）
    resample_files = [f for f in jp2_files if any(band in f for band in ["B05_20m", "B06_20m", "B07_20m", "B8A_20m", "B11_20m", "B12_20m"])]
    no_resample_files = [f for f in jp2_files if any(band in f for band in ["B02_10m", "B03_10m", "B04_10m", "B08_10m"])]
    files = resample_files + no_resample_files
    index_order = ['B02', 'B03', 'B04', 'B05', 'B06', 'B07', 'B08', 'B8A', 'B11', 'B12']
    physical_bands = ['B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B8A', 'B11', 'B12']
    band_descriptions = ['B02', 'B03', 'B04', 'B05', 'B06', 'B07', 'B08', 'B8A', 'B11', 'B12']
    ## 读取Sentinel-2A的元数据文件，获取指定波段的波长信息
    band_wavelengths = get_wavelength(product_uri_archive, physical_bands)
    wavelength_unit = 'Nanometers'  # 波长单位
    # 按照 index_order 的顺序排列 files 文件
    sorted_files = sorted(files, key=lambda f: next((i for i, band in enumerate(index_order) if band in f), float('inf')))

    crs, coords_res = get_coords_res(product_uri_archive)
    spacecraft_name = get_spacecraft_name(product_uri_archive)

    # # 找到所有波段中像素最大的宽度 和高度
    max_width = max_height = 0
    for file in resample_files + no_resample_files:
        with rasterio.open(rasterio_zipfile_path(product_uri_archive)+file) as src:
            max_width = max(max_width, src.width)
            max_height = max(max_height, src.height)


    data = []
    for file in sorted_files:
        with rasterio.open(rasterio_zipfile_path(product_uri_archive)+file) as src:
            if file in resample_files:
                print(f"{file}\n需要重采样")
                data.append(resample_data(rasterio_zipfile_path(product_uri_archive)+file)[0])
                new_transform = resample_data(rasterio_zipfile_path(product_uri_archive)+file)[1]
            else:
                print(f"{file}\n不需要重采样")
                data.append(no_resample_data(rasterio_zipfile_path(product_uri_archive)+file)[0])
                new_transform = no_resample_data(rasterio_zipfile_path(product_uri_archive)+file)[1]
    ulx = 699960.0
    uly = 2600040.0
    new_transform = rasterio.Affine.translation(ulx, uly) * rasterio.Affine.scale(10, -10)


    # 更新元数据
    out_meta = src.meta
    print(out_meta)
    out_meta.update({
        'driver': 'GTiff',
        'height': max_height,
        'width': max_width,
        'transform': new_transform,
        'crs': crs,  # 使用从元数据文件中获取的 CRS
        'res': (10.0, 10.0),
        'count': len(data),
        'description': f"Stacks of {spacecraft_name} bands B02, B03, B04, B05, B07, B08, B8A, B11, B12"  # 添加描述
    })

    print(out_meta)

    merged_data = np.concatenate(data, axis=0)

    # 写入新的 geotif 文件
    with rasterio.open(os.path.join(work_path, merged_product_uri_file), 'w', **out_meta) as dest:
        dest.write(merged_data)
        i = 1
        for i in range(1, dest.count+1):
            wavelength = band_wavelengths[physical_bands[i-1]]
            dest.update_tags(i, **wavelength)
            band_description = band_descriptions[i-1]
            dest.set_band_description(i, f"{spacecraft_name} Band {band_description}")



    dataset = gdal.Open(os.path.join(work_path, merged_product_uri_file))
    for i in range(1, dataset.RasterCount+1):
        band = dataset.GetRasterBand(i)
        # 获取元数据
        print(f"Band {i} color interpretation: {band.GetColorInterpretation()}")
        print(f"Band {i} description: {band.GetDescription()}")
        print(f"Band {i} metadata: {band.GetMetadata()}")
    dataset = None


    # 根据Geotiff生成hdr文件
    os.system(f"gdal_translate -of ENVI {os.path.join(work_path, merged_product_uri_file)} {os.path.join(work_path, merged_product_uri_file).replace('.tif', '.dat')}")


    ## 修改hdr文件
    modify_hdr_file(work_path, merged_product_uri_file_hdr, band_wavelengths, wavelength_unit)