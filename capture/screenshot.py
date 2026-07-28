import base64
from PySide6.QtCore import Qt, QBuffer, QIODevice, QCoreApplication, QEventLoop, QByteArray, QTimer
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
    _is_capturing = False
    _event_loop = None

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
            cls._is_capturing = False
            cls._event_loop = None

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
                    # 断开所有连接
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
    def _on_image_captured(cls, request_id, image):
        """相机捕获完成回调"""
        print(f"📷 捕获回调触发，请求ID: {request_id}")
        try:
            if image and not image.isNull():
                print(f"📷 图片尺寸: {image.width()}x{image.height()}")

                # 缩放图片
                if image.width() > 1920 or image.height() > 1080:
                    image = image.scaled(1920, 1080, Qt.KeepAspectRatio, Qt.SmoothTransformation)

                byte_array = QByteArray()
                buffer = QBuffer(byte_array)
                buffer.open(QIODevice.WriteOnly)
                image.save(buffer, "JPEG", 85)
                buffer.close()
                cls._capture_result = base64.b64encode(byte_array.data()).decode('utf-8')
                cls._capture_completed = True
                print("📷 图片捕获成功，大小: {} bytes".format(len(cls._capture_result)))
            else:
                print("⚠️ 捕获的图片为空或无效")
                cls._camera_error = True
        except Exception as e:
            print(f"处理相机图片失败: {e}")
            import traceback
            traceback.print_exc()
            cls._camera_error = True
        finally:
            # 退出事件循环
            if cls._event_loop and cls._event_loop.isRunning():
                cls._event_loop.quit()

    @classmethod
    def _on_capture_error(cls, request_id, error, error_string):
        """相机捕获错误回调"""
        print(f"❌ 相机捕获错误: {error_string} (错误码: {error})")
        cls._camera_error = True
        cls._capture_result = None
        cls._capture_completed = False
        # 退出事件循环
        if cls._event_loop and cls._event_loop.isRunning():
            cls._event_loop.quit()

    @classmethod
    def _on_camera_error(cls, error):
        """相机错误回调"""
        print(f"❌ 相机错误: {error}")
        cls._camera_error = True
        if cls._event_loop and cls._event_loop.isRunning():
            cls._event_loop.quit()

    @classmethod
    def capture_from_camera(cls):
        """使用相机拍摄照片"""
        if not QT_MULTIMEDIA_AVAILABLE or not cls.check_camera_available():
            return None

        if cls._is_capturing:
            print("⚠️ 相机正在捕获中")
            return None

        try:
            cls._is_capturing = True
            cls._cleanup_camera()

            # 获取默认相机
            camera_device = QMediaDevices.defaultVideoInput()
            if not camera_device:
                print("❌ 没有找到相机设备")
                cls._is_capturing = False
                return None

            print(f"📷 使用相机: {camera_device.description()}")

            # 创建相机和捕获会话
            cls._camera = QCamera(camera_device)
            cls._capture_session = QMediaCaptureSession()
            cls._image_capture = QImageCapture()

            # 设置图片质量
            cls._image_capture.setQuality(QImageCapture.HighQuality)

            cls._capture_session.setCamera(cls._camera)
            cls._capture_session.setImageCapture(cls._image_capture)

            cls._capture_result = None
            cls._capture_completed = False
            cls._camera_error = False

            # 连接信号
            cls._image_capture.imageCaptured.connect(cls._on_image_captured)
            cls._image_capture.errorOccurred.connect(cls._on_capture_error)

            # 启动相机
            cls._camera.start()

            # 等待相机稳定
            print("⏳ 等待相机启动...")
            QTimer.singleShot(500, lambda: None)
            QCoreApplication.processEvents()

            # 创建事件循环等待捕获完成
            cls._event_loop = QEventLoop()

            # 设置超时定时器（3秒）
            timeout_timer = QTimer()
            timeout_timer.setSingleShot(True)
            timeout_timer.timeout.connect(lambda: cls._on_capture_timeout())

            print("📷 开始捕获...")
            # 执行捕获
            if cls._image_capture:
                cls._image_capture.capture()
                # 启动超时定时器
                timeout_timer.start(3000)
                # 进入事件循环等待
                cls._event_loop.exec()

                # 检查结果 - 确保返回有效的 base64 字符串
                if cls._capture_result is not None and isinstance(cls._capture_result, str) and len(cls._capture_result) > 100:
                    result = cls._capture_result
                    print(f"📷 相机拍照成功，Base64长度: {len(result)}")
                    cls._cleanup_camera()
                    cls._is_capturing = False
                    return result
                else:
                    print(f"⚠️ 相机拍照失败，结果: {type(cls._capture_result)}")
                    cls._cleanup_camera()
                    cls._is_capturing = False
                    return None
            else:
                print("❌ 图像捕获对象无效")
                cls._cleanup_camera()
                cls._is_capturing = False
                return None

        except Exception as e:
            print(f"❌ 相机拍照失败: {e}")
            import traceback
            traceback.print_exc()
            cls._cleanup_camera()
            cls._is_capturing = False
            return None

    @classmethod
    def _on_capture_timeout(cls):
        """捕获超时处理"""
        print("⏰ 相机捕获超时")
        cls._camera_error = True
        if cls._event_loop and cls._event_loop.isRunning():
            cls._event_loop.quit()

    @staticmethod
    def capture_screenshot():
        """捕获当前屏幕截图"""
        try:
            screen = QGuiApplication.primaryScreen()
            if screen:
                screenshot = screen.grabWindow(0)
                img = screenshot.toImage()
                if img.width() > 1920:
                    img = img.scaled(1920, 1080, Qt.KeepAspectRatio, Qt.SmoothTransformation)

                byte_array = QByteArray()
                buffer = QBuffer(byte_array)
                buffer.open(QIODevice.WriteOnly)
                img.save(buffer, "JPEG", 85)
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

        if use_camera and QT_MULTIMEDIA_AVAILABLE and cls.check_camera_available():
            print("📷 尝试使用相机拍摄...")
            result = cls.capture_from_camera()
            if result:
                print("📷 使用相机拍摄成功")
                return result
            else:
                print("📷 相机拍摄失败，尝试截图...")

        if use_screenshot:
            result = cls.capture_screenshot()
            if result:
                print("🖥️ 使用截图成功")
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