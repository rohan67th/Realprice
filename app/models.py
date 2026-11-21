from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
import uuid

class CustomUserManager(BaseUserManager):
    def create_user(self, username, email, phone, address, gender,password=None,**extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        user = self.model(
            username=username,
            email=self.normalize_email(email),
            phone=phone,
            address=address,
            gender=gender,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email,password,**extra_fields):
        user = self.create_user(
            username=username,
            email=email,
            phone='N/A',
            address='N/A',
            gender='Other',
            password=password,
            **extra_fields
        )
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class CustomUser(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15)
    address = models.TextField()
    gender = models.CharField(max_length=10)
    profile_pic = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    proof_of_identity = models.FileField(upload_to='identity_proofs/', null=True, blank=True)
    
    # Role-based identity
    ROLE_CHOICES = [
        ('seller', 'Seller'),
        ('admin', 'Admin'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='seller')

    # Seller approval workflow
    REVIEW_STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('changes_requested', 'Changes Requested'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    review_status = models.CharField(
        max_length=20, choices=REVIEW_STATUS_CHOICES, default='pending'
    )

    is_blocked = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    block_reason = models.TextField(blank=True, default='')
    rejection_reason = models.TextField(blank=True, default='')
    date_joined = models.DateTimeField(auto_now_add=True, null=True)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    objects = CustomUserManager()

    def __str__(self):
        return self.username

    def get_full_name(self):
        return self.username

    def get_short_name(self):
        return self.username


class PasswordReset(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    reset_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_when = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Password reset for {self.user.username} at {self.created_when}"
    



from django.utils.text import slugify
from django.conf import settings

class Property(models.Model):
    PROPERTY_TYPES = [
        ('House', 'House'),
        ('Apartment', 'Apartment'),
        ('Commercial', 'Commercial'),
        ('Land', 'Land'),
    ]

    STATUS_CHOICES = [
        ('Available', 'Available'),
        ('Sold', 'Sold'),
        ('Rented', 'Rented'),
    ]

    LISTING_TYPE_CHOICES = [
        ('sale', 'For Sale'),
        ('rent', 'For Rent'),
    ]

    # Property approval workflow — extensible status list
    APPROVAL_STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('changes_requested', 'Changes Requested'),
        # Future statuses can be added here, e.g.:
        # ('blocked', 'Blocked'),
        # ('suspended', 'Suspended'),
    ]

    property_type = models.CharField(max_length=50, choices=PROPERTY_TYPES)
    address = models.TextField()
    location = models.CharField(max_length=100)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    area_sqft = models.FloatField(null=True, blank=True)
    bedrooms = models.PositiveIntegerField(null=True, blank=True)
    bathrooms = models.PositiveIntegerField(null=True, blank=True)

    features = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)

    main_image = models.ImageField(upload_to='property_photos/', null=True, blank=True)
    image_1 = models.ImageField(upload_to='property_photos/', null=True, blank=True)
    image_2 = models.ImageField(upload_to='property_photos/', null=True, blank=True)
    image_3 = models.ImageField(upload_to='property_photos/', null=True, blank=True)

    price = models.DecimalField(max_digits=12, decimal_places=2)
    previous_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text='Set when price is lowered, to show "Price Drop" badge.'
    )
    listing_type = models.CharField(
        max_length=4, choices=LISTING_TYPE_CHOICES, default='sale',
        db_index=True,
        help_text='Whether this property is for sale or for rent.'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Available')

    seller = models.ForeignKey(CustomUser, on_delete=models.CASCADE)

    # Legacy field — kept for backward compatibility with existing queries
    is_approved = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)

    # New approval workflow fields
    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS_CHOICES,
        default='pending',
        db_index=True,
    )
    admin_notes = models.TextField(blank=True, default='')       # Internal — NOT visible to seller
    seller_feedback = models.TextField(blank=True, default='')   # Message TO seller (reject/changes)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_properties',
    )

    posted_at = models.DateTimeField(auto_now_add=True)

    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        # Keep is_approved in sync with approval_status
        self.is_approved = (self.approval_status == 'approved')
        if not self.slug:
            self.slug = slugify(f"{self.property_type}-{self.location}-{self.pk}")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.property_type} at {self.location} - ₹{self.price}"

    def get_approval_badge_class(self):
        """Return CSS badge class for the approval status."""
        return {
            'pending': 'badge-warning',
            'approved': 'badge-success',
            'rejected': 'badge-danger',
            'changes_requested': 'badge-warning',
        }.get(self.approval_status, 'badge-neutral')

    def get_approval_display_label(self):
        """Return human-readable label for approval status."""
        return dict(self.APPROVAL_STATUS_CHOICES).get(self.approval_status, self.approval_status)


class PropertyAuditLog(models.Model):
    """Tracks every approval action taken on a property listing."""
    ACTION_CHOICES = [
        ('approve', 'Approved'),
        ('reject', 'Rejected'),
        ('request_changes', 'Requested Changes'),
        ('resubmit', 'Resubmitted by Seller'),
    ]

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='audit_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    admin_user = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='property_admin_actions',
    )
    notes = models.TextField(blank=True, default='')            # Internal admin notes
    seller_feedback = models.TextField(blank=True, default='')  # Message sent to seller
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_action_display()} — Property #{self.property_id} by {self.admin_user}"


class SellerAuditLog(models.Model):
    ACTION_CHOICES = [
        ('approve', 'Approved'),
        ('reject', 'Rejected'),
        ('request_changes', 'Requested Changes'),
        ('resubmit', 'Resubmitted'),
        ('block', 'Blocked'),
        ('unblock', 'Unblocked'),
    ]

    seller = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='audit_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    admin_user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='admin_actions')
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_action_display()} — {self.seller.username} by {self.admin_user}"
