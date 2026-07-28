import base64
from PySide6.QtCore import QBuffer, QIODevice, QCoreApplication, QEventLoop, QByteArray, QTimer
from PySide6.QtGui import QGuiApplication

# 尝试导入 QtMultimedia
try:
    from PySide6.QtMultimedia import (
        QCamera, QCameraDevice, QMediaDevices,
        QMediaCaptureSession, QImageCapture
    )
    QT_MULTIMEDIA_AVAILABLE = True
    print("✅ QtMultimedia 模块加载成功")
except ImportError as e:
    QT_MULTIMEDIA_AVAILABLE = False
    QCamera = None
    QCameraDevice = None
    QMediaDevices = None
    QMediaCaptureSession = None
    QImageCapture = None
    print(f"⚠️ QtMultimedia 模块不可用: {e}")


class ScreenshotManager:
    """截图/相机管理器 - 统一处理媒体捕获"""

    _camera = None
    _capture_session = None
    _image_capture = None
    _camera_available = None
    _capture_result = None
    _capture_completed = False
    _camera_error = False

    @classmethod
    def check_camera_available(cls):
        """检查是否有可用的相机"""
        if not QT_MULTIMEDIA_AVAILABLE:
            cls._camera_available = False
            return False

        if cls._camera_available is not None:
            return cls._camera_available

        try:
            default_camera = QMediaDevices.defaultVideoInput()
            if default_camera:
                cls._camera_available = True
                print("📷 检测到可用相机")
                return True
            else:
                cls._camera_available = False
                print("📷 未检测到可用相机，使用截图模式")
                return False
        except Exception as e:
            print(f"相机检测失败: {e}")
            cls._camera_available = False
            return False

    @classmethod
    def _cleanup_camera(cls):
        """彻底清理相机资源"""
        try:
            if cls._camera:
                try:
                    cls._camera.stop()
                except:
                    pass
                cls._camera = None

            if cls._capture_session:
                try:
                    cls._capture_session.setCamera(None)
                    cls._capture_session.setImageCapture(None)
                except:
                    pass
                cls._capture_session = None

            if cls._image_capture:
                try:
                    cls._image_capture.imageCaptured.disconnect()
                    cls._image_capture.errorOccurred.disconnect()
                except:
                    pass
                cls._image_capture = None

            cls._capture_result = None
            cls._capture_completed = False
            cls._camera_error = False
            QCoreApplication.processEvents()
        except Exception as e:
            print(f"清理相机资源时出错: {e}")

    @classmethod
    def capture_from_camera(cls):
        """使用相机拍摄照片"""
        if not QT_MULTIMEDIA_AVAILABLE or not cls.check_camera_available():
            return None

        try:
            cls._cleanup_camera()
            QTimer.singleShot(200, lambda: None)
            QCoreApplication.processEvents()

            camera_device = QMediaDevices.defaultVideoInput()
            if not camera_device:
                return None

            cls._camera = QCamera(camera_device)
            cls._capture_session = QMediaCaptureSession()
            cls._image_capture = QImageCapture()
            cls._capture_session.setCamera(cls._camera)
            cls._capture_session.setImageCapture(cls._image_capture)

            cls._capture_result = None
            cls._capture_completed = False
            cls._camera_error = False

            cls._image_capture.imageCaptured.connect(cls._on_image_captured)
            cls._image_capture.errorOccurred.connect(cls._on_capture_error)

            cls._camera.start()

            # 等待相机准备就绪
            loop = QEventLoop()
            QTimer.singleShot(3000, loop.quit)
            loop.exec()

            if not cls._camera or cls._camera_error:
                print("⚠️ 相机启动失败")
                cls._cleanup_camera()
                return None

            print("📷 相机已启动，准备拍摄...")
            QTimer.singleShot(200, lambda: None)
            QCoreApplication.processEvents()

            if cls._image_capture:
                cls._image_capture.capture()

            # 等待捕获完成
            wait_cycles = 0
            while cls._capture_result is None and not cls._camera_error and wait_cycles < 150:
                QCoreApplication.processEvents()
                QTimer.singleShot(20, lambda: None)
                wait_cycles += 1

            result = cls._capture_result
            cls._cleanup_camera()

            if result:
                print("📷 相机拍照成功")
                return result
            else:
                if cls._camera_error:
                    print("⚠️ 相机捕获出错")
                else:
                    print("⚠️ 相机拍照超时")
                return None

        except Exception as e:
            print(f"相机拍照失败: {e}")
            cls._cleanup_camera()
            return None

    @classmethod
    def _on_image_captured(cls, request_id, image):
        """相机捕获完成回调"""
        try:
            if image and not image.isNull():
                byte_array = QByteArray()
                buffer = QBuffer(byte_array)
                buffer.open(QIODevice.WriteOnly)
                image.save(buffer, "PNG")
                buffer.close()
                cls._capture_result = base64.b64encode(byte_array.data()).decode('utf-8')
                cls._capture_completed = True
                print("📷 图片捕获成功")
            else:
                print("⚠️ 捕获的图片为空")
                cls._camera_error = True
        except Exception as e:
            print(f"处理相机图片失败: {e}")
            cls._camera_error = True

    @classmethod
    def _on_capture_error(cls, request_id, error, error_string):
        """相机捕获错误回调"""
        print(f"相机捕获错误: {error_string}")
        cls._camera_error = True
        cls._capture_result = None

    @staticmethod
    def capture_screenshot():
        """捕获当前屏幕截图"""
        try:
            screen = QGuiApplication.primaryScreen()
            if screen:
                screenshot = screen.grabWindow(0)
                img = screenshot.toImage()
                byte_array = QByteArray()
                buffer = QBuffer(byte_array)
                buffer.open(QIODevice.WriteOnly)
                img.save(buffer, "PNG")
                buffer.close()
                return base64.b64encode(byte_array.data()).decode('utf-8')
            return None
        except Exception as e:
            print(f"截图失败: {e}")
            return None

    @classmethod
    def capture_media(cls, use_camera=True, use_screenshot=True):
        """捕获媒体（根据设置选择方式）"""
        result = None

        # 优先尝试相机
        if use_camera and QT_MULTIMEDIA_AVAILABLE and cls.check_camera_available():
            result = cls.capture_from_camera()
            if result:
                print("📷 使用相机拍摄")
                return result
            else:
                print("📷 相机拍摄失败")

        # 备用方案：截图
        if use_screenshot:
            result = cls.capture_screenshot()
            if result:
                print("🖥️ 使用截图")
                return result
            else:
                print("⚠️ 截图失败")

        return None

    @staticmethod
    def base64_to_pixmap(base64_str):
        """将 base64 字符串转换为 QPixmap"""
        if not base64_str:
            return None
        try:
            from PySide6.QtGui import QPixmap
            data = base64.b64decode(base64_str)
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            return pixmap
        except Exception as e:
            print(f"转换图片失败: {e}")
            return None
