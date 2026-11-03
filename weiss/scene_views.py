"""Scenes on the staff's CPU creation tab: writing them, checking them as they're written, and playing them to test."""
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from . import scenes
from .cpu_views import staff_required
from .models import CpuProfile, Scene


@staff_required
@require_POST
def scene_create(request):
    name = request.POST.get("name", "").strip()[:100]
    if not name:
        messages.error(request, "Give the scene a name.")
        return redirect("weiss:cpu_home")
    if Scene.objects.filter(name=name).exists():
        messages.error(request, f"There's already a scene called {name}.")
        return redirect("weiss:cpu_home")
    scene = Scene.objects.create(name=name, script=scenes.starter_script(list(CpuProfile.objects.all()[:1])), created_by=request.user)
    return redirect("weiss:cpu_scene_edit", pk=scene.pk)


@staff_required
def scene_edit(request, pk):
    """The script, its mistakes, and the reference. Saving keeps a script with mistakes, so work isn't lost."""
    scene = get_object_or_404(Scene, pk=pk)
    if request.method == "POST":
        name = request.POST.get("name", "").strip()[:100] or scene.name
        if Scene.objects.filter(name=name).exclude(pk=scene.pk).exists():
            messages.error(request, f"There's already a scene called {name}; the name is unchanged.")
            name = scene.name
        scene.name = name
        scene.script = request.POST.get("script", "").replace("\r\n", "\n")[:scenes.MAX_SCRIPT]
        scene.save()
        errors = scenes.compile_scene(scene.script)[1]
        if errors:
            messages.warning(request, f"Saved, with {len(errors)} mistake{'s' if len(errors) != 1 else ''} to fix before it can be played.")
        elif request.POST.get("then") == "play":
            return redirect("weiss:cpu_scene_play", pk=scene.pk)
        else:
            messages.success(request, "Saved.")
        return redirect("weiss:cpu_scene_edit", pk=scene.pk)
    compiled, errors = scenes.compile_scene(scene.script)
    profiles = list(CpuProfile.objects.all())
    for profile in profiles:
        profile.cast_name = scenes.cast_name(profile)
    return render(request, "weiss/scene_edit.html", {
        "scene": scene, "errors": errors, "labels": sorted(compiled["labels"]), "reference": scenes.REFERENCE,
        "profiles": profiles, "max_script": scenes.MAX_SCRIPT,
        "animations": scenes.ACTIONS,
    })


@staff_required
@require_POST
def scene_check(request, pk):
    """The editor checks the script as it's typed: its mistakes and labels, without saving it."""
    get_object_or_404(Scene, pk=pk)
    compiled, errors = scenes.compile_scene(request.POST.get("script", "")[:scenes.MAX_SCRIPT + 1])
    return JsonResponse({"errors": errors, "labels": sorted(compiled["labels"])})


@staff_required
def scene_play(request, pk):
    """Play the scene as a player would see it, with a panel showing where it's got to. ?from=label starts there."""
    scene = get_object_or_404(Scene, pk=pk)
    compiled, errors = scenes.compile_scene(scene.script)
    if errors:
        messages.error(request, "Fix the script's mistakes before playing it.")
        return redirect("weiss:cpu_scene_edit", pk=scene.pk)
    start = request.GET.get("from", "").lower()
    return render(request, "weiss/scene_play.html", {
        "scene": scene, "payload": scenes.scene_payload(compiled, scene.name), "labels": sorted(compiled["labels"]),
        "start": start if start in compiled["labels"] else "", "player_name": request.user.username,
    })


@staff_required
@require_POST
def scene_delete(request, pk):
    scene = get_object_or_404(Scene, pk=pk)
    scene.delete()
    messages.success(request, f"Deleted {scene.name}.")
    return redirect("weiss:cpu_home")
