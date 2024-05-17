from django.db import models

# Create your models here.

class User(models.Model):
    name = models.CharField(max_length=200, null=True)
    phone = models.CharField(max_length=200, null=True)
    email = models.CharField(max_length=200, null=True)
    date_created = models.DateTimeField(auto_now_add=True, null=True)


    def __str__(self):
        return self.name

class History(models.Model):
    file = models.FileField(upload_to="files")

    STATUS = (
        ('save', 'save'),
        ('delete', 'delete'),
    )

    date_created = models.DateTimeField(auto_now_add=True, null=True)
    status = models.CharField(max_length=200, null=True, choices=STATUS)
def __str__(self):
        return self.history

class TableRecognitionImage(models.Model):
    id = models.AutoField(primary_key=True)
    record_date = models.DateTimeField(auto_now_add=True)
    image = models.ImageField(upload_to='uploads/')

    def __str__(self):
        return str(self.image)

class TableRecognitionFile(models.Model):
    id = models.AutoField(primary_key=True)
    record_date = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to='uploads/')

    def __str__(self):
        return str(self.image)
    


