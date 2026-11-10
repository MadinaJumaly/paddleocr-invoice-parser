from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import ProfileForm, RecognitionForm, SignUpForm, UserForm
from .models import Profile, Recognition
from .recognition import run_recognition


# --- Главная ----------------------------------------------------------------

def home(request):
    return render(request, "main/home.html", {"max_pages": settings.OCR_MAX_PAGES})


# --- Авторизация ------------------------------------------------------------

def signup(request):
    if request.user.is_authenticated:
        return redirect("recognition")
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        Profile.objects.create(user=user)
        login(request, user)
        messages.success(request, "Аккаунт создан. Добро пожаловать!")
        return redirect("recognition")
    return render(request, "main/signup.html", {"form": form})


# --- Распознавание ----------------------------------------------------------

@login_required
def recognition(request):
    form = RecognitionForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.user = request.user
        item.original_name = request.FILES["source"].name[:255]
        item.save()
        run_recognition(item)  # synchronous: takes a few seconds per page on CPU
        if item.status == Recognition.Status.DONE:
            messages.success(request, f"Найдено таблиц: {len(item.tables)}.")
        elif item.status == Recognition.Status.EMPTY:
            messages.warning(request, "В документе не найдено таблиц.")
        else:
            messages.error(request, item.error)
        return redirect("recognition_detail", pk=item.pk)

    recent = request.user.recognitions.all()[:5]
    return render(request, "main/recognition.html", {"form": form, "recent": recent})


def _own(request, pk):
    return get_object_or_404(Recognition, pk=pk, user=request.user)


@login_required
def recognition_detail(request, pk):
    return render(request, "main/recognition_detail.html", {"item": _own(request, pk)})


@login_required
def download_result(request, pk):
    item = _own(request, pk)
    if not item.result:
        raise Http404
    return FileResponse(item.result.open("rb"), as_attachment=True, filename=item.result_name)


@login_required
def download_source(request, pk):
    item = _own(request, pk)
    return FileResponse(item.source.open("rb"), as_attachment=True, filename=item.original_name)


@login_required
@require_POST
def recognition_delete(request, pk):
    item = _own(request, pk)
    item.delete_files()
    item.delete()
    messages.success(request, f"«{item.original_name}» удалён из истории.")
    return redirect("history")


# --- История ----------------------------------------------------------------

@login_required
def history(request):
    items = request.user.recognitions.all()
    status = request.GET.get("status")
    if status in Recognition.Status.values:
        items = items.filter(status=status)
    page = Paginator(items, 20).get_page(request.GET.get("page"))
    return render(request, "main/history.html", {
        "page": page,
        "status": status,
        "statuses": Recognition.Status.choices,
    })


# --- Пользователь -----------------------------------------------------------

@login_required
def profile(request):
    prof, _ = Profile.objects.get_or_create(user=request.user)
    user_form = UserForm(request.POST or None, instance=request.user)
    profile_form = ProfileForm(request.POST or None, instance=prof)
    if request.method == "POST" and user_form.is_valid() and profile_form.is_valid():
        user_form.save()
        profile_form.save()
        messages.success(request, "Профиль сохранён.")
        return redirect("profile")

    items = request.user.recognitions
    stats = {
        "total": items.count(),
        "done": items.filter(status=Recognition.Status.DONE).count(),
        "failed": items.filter(status=Recognition.Status.FAILED).count(),
    }
    return render(request, "main/profile.html", {
        "user_form": user_form,
        "profile_form": profile_form,
        "stats": stats,
    })
