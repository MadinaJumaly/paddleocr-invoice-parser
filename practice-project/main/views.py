from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.middleware.csrf import get_token
from django.db import IntegrityError      
from django.contrib.auth import login, logout, authenticate
from django.http import HttpResponse
from django.core.files.storage import FileSystemStorage
from PIL import Image
from .models import TableRecognitionImage, TableRecognitionFile
from .forms import UploadFileForm, UploadFileForm2, UploadImageForm

def home(request):
           
           return render(request, 'main/home.html')
def userprofile(request):
    return render(request, 'main/userprofile.html')

def signupuser(request):
    if request.method == 'GET':
       return render(request, 'main/signupuser.html', {'form':UserCreationForm()})
    else:
        if request.POST['password1'] == request.POST['password2']:
             try:
                 user = User.objects.create_user(request.POST['username'], password=request.POST['password1'])
                 user.save()
                 login(request, user)
                 return redirect('currentfile')
             except IntegrityError:
                 return render(request, 'main/signupuser.html', {'form':UserCreationForm(), 'error':'That username has already been taken. Please choose a new username'})

             else: 
                 return render(request, 'main/signupuser.html', {'form':UserCreationForm(), 'error':'Passwords did not match'})

def loginuser(request):
     if request.method == 'GET':
       return render(request, 'main/loginuser.html', {'form':AuthenticationForm()})
     else:
         user = authenticate(request, username=request.POST['username'], password=request.POST['password'])
         if user is None:
              return render(request, 'main/loginuser.html', {'form':AuthenticationForm(), 'error': 'Username and password did not match'})
         else: 
            login(request, user)
            return redirect('currentfile') 

         

def logoutuser(request):
    if request.method == 'POST':
        logout(request)
        return  redirect ('main/home.html')

def currentfile(request):
    return render(request, 'main/currentfile.html')
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import UploadImageForm

def upload_image(request):
    if request.method == 'POST':
        form = UploadImageForm(request.POST, request.FILES)
        if form.is_valid():
            # Process the uploaded image
            image = form.save(commit=False)
            # If needed, do additional processing with the image here
            image.save()
            messages.success(request, 'Image uploaded successfully.')
            return redirect('currentfile')  # Redirect to a page displaying uploaded images
        else:
            messages.error(request, 'Error uploading image. Please check the form.')
    else:
        form = UploadImageForm()
    return render(request, 'upload_image.html', {'form': form})


def view_name(request):
    csrf_token = get_token(request)

    # perform view logic
    context = {
        "csrf_token": csrf_token
    }

    return render(request, 'app_name/template.html', context=context)

def user(request):
    return render(request, 'main/userprofile.html')

   
     
def index(request):
	indexActive = 'active'
	pageTitle = 'Greyscale'
	pageStatus = 1
	if request.method == 'POST':
		uploaded_file = request.FILES['imagefile']
		pageStatus = 2
		fs = FileSystemStorage()
		name = fs.save(uploaded_file.name, uploaded_file)
		url = fs.url(name)
		displayFile = url
		tujuan = "/srv/http/practice-project" + url
		gambarGreyscale = Image.open(tujuan)
		namafilebaru = tujuan[:-4] + "_greyscale" + tujuan[-4:]
		# CONVERT MULAI DISINI MENGGUNAKAN FUNGSI convert()
		filebaru = gambarGreyscale.convert(mode='L').save(namafilebaru)
		displayFileMod = url[:-4] + "_greyscale" + url[-4:]
		return render(request, 'main/base.html', {
			'pageStatus':pageStatus,
			'displayFileMod':displayFileMod,
			'pageTitle':pageTitle,
			'indexActive':indexActive,
			'displayFile':displayFile
			})
	return render(request, 'main/base.html', {
		'pageStatus':pageStatus,
		'pageTitle':pageTitle,
		'indexActive':indexActive
		})


def upload_and_display_files(request):
    files = TableRecognitionFile.objects.all()

    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            for uploaded_file in request.FILES.getlist('files'):
                TableRecognitionFile.objects.create(file=uploaded_file)
            return redirect('upload_and_display')
    else:
        form = UploadFileForm()

    return render(request, 'upload_and_display.html', {'form': form, 'files': files})

def upload_file(request):
    if request.method == 'POST':
        form = UploadFileForm2(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('upload_file')
    else:
        form = UploadFileForm2()
    files = TableRecognitionFile.objects.all()
    return render(request, 'upload_file.html', {'form': form, 'files': files})

def download_file(request, file_id):
    uploaded_file = TableRecognitionFile.objects.get(pk=file_id)
    response = HttpResponse(uploaded_file.file, content_type='application/force-download')
    response['Content-Disposition'] = f'attachment; filename="{uploaded_file.file.name}"'
    return response

def upload_image(request):
    if request.method == 'POST':
        form = UploadImageForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
    else:
        form = UploadImageForm()
    images = TableRecognitionImage.objects.all()

    return render(request, 'upload_image.html', {'form': form, 'images': images})





