from django.db import models
from django.utils.text import slugify

class Product(models.Model):
    CATEGORY = (("Electronics","ELECTRONICS"),
               ("Groceries","GROCERIES"),
               ("Clothings","CLOTHINGS"))
    name= models.CharField(max_length=100)
    slug= models.SlugField(blank=1,null=1)
    image= models.ImageField(upload_to="products/")
    description= models.TextField(blank=1,null=1)
    price= models.DecimalField(max_digits=10, decimal_places=2)
    category= models.CharField(max_length=15,choices=CATEGORY,blank=1,null=1)

    def __str__(self):
        return self.name
    

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            unique_slug = self.slug
            counter = 1
            if Product.objects.filter(slug=unique_slug).exists():
                unique_slug = f'{self.slug}-{counter}'
                counter += 1
            self.slug = unique_slug
        super().save(*args, **kwargs)
    