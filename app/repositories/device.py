from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.device import Device
from app.schemas.device import DeviceUpdate

class DeviceRepository:
    """
    Isolates database operations for RTSP Devices.
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session

    def get_all(self, user_id: int) -> List[Device]:
        return self.db.query(Device).filter(Device.user_id == user_id).all()

    def get_all_system_devices(self) -> List[Device]:
        return self.db.query(Device).all()

    def get_by_id(self, device_id: int) -> Optional[Device]:
        return self.db.query(Device).filter(Device.id == device_id).first()

    def get_by_ip(self, ip_address: str) -> Optional[Device]:
        return self.db.query(Device).filter(Device.ip_address == ip_address).first()

    def create(self, ip_address: str, port: int, username: str, password: str, rtsp_url: str, manufacturer: str, user_id: int) -> Device:
        db_device = Device(
            ip_address=ip_address,
            port=port,
            username=username,
            password=password,
            rtsp_url=rtsp_url,
            manufacturer=manufacturer,
            name=f"Cam {ip_address.split('.')[-1]}",
            is_configured=True,
            user_id=user_id # Vincula a câmera ao cliente
        )
        self.db.add(db_device)
        self.db.commit()
        self.db.refresh(db_device)
        return db_device

    def update(self, device_id: int, config: DeviceUpdate, rtsp_url: Optional[str] = None) -> Optional[Device]:
        dev = self.get_by_id(device_id)
        if dev:
            # model_dump(exclude_unset=True) ensures we only update fields the user actually sent
            update_data = config.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(dev, key, value)
            
            if rtsp_url:
                dev.rtsp_url = rtsp_url
                
            dev.is_configured = True
            self.db.commit()
            self.db.refresh(dev)
        return dev

    def delete(self, device_id: int) -> bool:
        dev = self.get_by_id(device_id)
        if dev:
            self.db.delete(dev)
            self.db.commit()
            return True
        return False