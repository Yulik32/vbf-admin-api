from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(200), nullable=True)
    role = Column(String(20), default="admin")  # "admin" или "user"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Card(Base):
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    order = Column(Integer, default=0)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class SiteSetting(Base):
    __tablename__ = "site_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True, nullable=False)
    value = Column(Text, nullable=True)
    description = Column(String(500), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# Главная
class UploadedMedia(Base):
    __tablename__ = "uploaded_media"
    
    id = Column(Integer, primary_key=True, index=True)
    page = Column(String(50), nullable=False, index=True)  # 'main', 'history', etc.
    section = Column(String(100), nullable=False)  # 'offer_background', 'gallery', etc.
    filename = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    mime_type = Column(String(100))
    alt_ru = Column(String(500), nullable=True)
    alt_en = Column(String(500), nullable=True)
    order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)

class PageContent(Base):
    __tablename__ = "page_contents"
    
    id = Column(Integer, primary_key=True, index=True)
    page = Column(String(50), nullable=False, index=True)
    section = Column(String(100), nullable=False)
    language = Column(String(2), nullable=False)
    content = Column(Text, nullable=True)
    content_type = Column(String(20), default='text')  # 'text', 'image', 'url', 'html'
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)

class GalleryImage(Base):
    __tablename__ = "gallery_images"
    
    id = Column(Integer, primary_key=True, index=True)
    page = Column(String(50), nullable=False)  # 'main', 'catalog' и т.д.
    image_url = Column(String(500), nullable=False)
    image_order = Column(Integer, default=0)
    alt_ru = Column(String(200), nullable=True)
    alt_en = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class RealtyAddress(Base):
    __tablename__ = "realty_addresses"
    
    id = Column(Integer, primary_key=True, index=True)
    address_ru = Column(Text, nullable=False)
    address_en = Column(Text, nullable=False)
    map_link = Column(String(500), nullable=True)  # Одна ссылка
    order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)

class Manager(Base):
    __tablename__ = "managers"
    
    id = Column(Integer, primary_key=True, index=True)
    name_ru = Column(String(200), nullable=False)
    name_en = Column(String(200), nullable=False)
    position_ru = Column(String(200), nullable=False)
    position_en = Column(String(200), nullable=False)
    phone = Column(String(50), nullable=True)
    photo_url = Column(String(500), nullable=True)
    order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)

class ServicePhone(Base):
    __tablename__ = "service_phones"
    
    id = Column(Integer, primary_key=True, index=True)
    section_key = Column(String(100), nullable=False, index=True)  # sales, supply
    title_ru = Column(String(200), nullable=False)
    title_en = Column(String(200), nullable=False)
    phone = Column(String(50), nullable=True)
    order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)

class OxranaDocument(Base):
    __tablename__ = "oxrana_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    title_ru = Column(String(300), nullable=False)
    title_en = Column(String(300), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_name = Column(String(200), nullable=True)
    file_size = Column(Integer, nullable=True)
    order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)

class QualityCard(Base):
    __tablename__ = "quality_cards"
    
    id = Column(Integer, primary_key=True, index=True)
    image_url = Column(String(500), nullable=False)
    title_ru = Column(String(500), nullable=False)
    title_en = Column(String(500), nullable=False)
    description_ru = Column(Text, nullable=False)
    description_en = Column(Text, nullable=False)
    certificate_url = Column(String(500), nullable=True)
    order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)

class LicenseContent(Base):
    __tablename__ = "license_content"
    
    id = Column(Integer, primary_key=True, index=True)
    text_ru = Column(Text, nullable=False)
    text_en = Column(Text, nullable=False)
    link_text_ru = Column(String(200), nullable=True)
    link_text_en = Column(String(200), nullable=True)
    link_description_ru = Column(Text, nullable=True)
    link_description_en = Column(Text, nullable=True)
    image_1_url = Column(String(500), nullable=True)
    image_2_url = Column(String(500), nullable=True)
    quality_title_ru = Column(String(200), nullable=True)
    quality_title_en = Column(String(200), nullable=True)
    licenses_title_ru = Column(String(200), nullable=True)
    licenses_title_en = Column(String(200), nullable=True)

    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)

class CatalogCard(Base):
    __tablename__ = "catalog_cards"
    
    id = Column(Integer, primary_key=True, index=True)
    title_ru = Column(String(300), nullable=False)
    title_en = Column(String(300), nullable=False)
    description_ru = Column(Text, nullable=True)
    description_en = Column(Text, nullable=True)
    file_url = Column(String(500), nullable=True)  # PDF или HTML файл
    icon_type = Column(String(50), default="one")  # one, two, three
    order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)

class CatalogSettings(Base):
    __tablename__ = "catalog_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    design_dept_phone_ru = Column(String(100), nullable=True)
    design_dept_phone_en = Column(String(100), nullable=True)
    planning_dept_phone_ru = Column(String(100), nullable=True)
    planning_dept_phone_en = Column(String(100), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())