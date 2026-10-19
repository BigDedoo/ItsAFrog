#include "FrogLevelHUD.h"

#include "CanvasItem.h"
#include "Engine/Canvas.h"
#include "Engine/Font.h"
#include "FrogLevelGameMode.h"
#include "UObject/ConstructorHelpers.h"

#define LOCTEXT_NAMESPACE "FrogLevel"

namespace
{
	// Palette: warm firelight on a cool night.
	const FLinearColor Gold(1.0f, 0.8f, 0.36f);
	const FLinearColor Warm(1.0f, 0.93f, 0.82f);
	const FLinearColor Cool(0.72f, 0.8f, 1.0f);
	const FLinearColor Night(0.02f, 0.035f, 0.09f);

	FLinearColor WithAlpha(FLinearColor Color, float Alpha)
	{
		Color.A *= FMath::Clamp(Alpha, 0.0f, 1.0f);
		return Color;
	}

	/** 0 -> 1 over FadeIn, holds, then 1 -> 0 over the last FadeOut seconds of Duration. */
	float FadeEnvelope(float Age, float Duration, float FadeIn, float FadeOut)
	{
		if (Age < 0.0f || Age > Duration)
		{
			return 0.0f;
		}
		return FMath::Min(Age / FMath::Max(FadeIn, 0.01f), (Duration - Age) / FMath::Max(FadeOut, 0.01f));
	}

	FText Clock(float Seconds)
	{
		const int32 Whole = FMath::Max(0, FMath::FloorToInt(Seconds));
		return FText::FromString(FString::Printf(TEXT("%d:%02d"), Whole / 60, Whole % 60));
	}
}

AFrogLevelHUD::AFrogLevelHUD()
{
	static ConstructorHelpers::FObjectFinder<UFont> Roboto(TEXT("/Engine/EngineFonts/Roboto.Roboto"));
	if (Roboto.Succeeded())
	{
		FontObject = Roboto.Object;
	}
}

FSlateFontInfo AFrogLevelHUD::Font(float Size, FName Typeface) const
{
	return FSlateFontInfo(FontObject, FMath::Max(1, FMath::RoundToInt(Size * UIScale)), Typeface);
}

void AFrogLevelHUD::Text(const FText& InText, float X, float Y, float Size, const FLinearColor& Color, bool bCentre, FName Typeface)
{
	if (Color.A <= 0.01f)
	{
		return;
	}
	FCanvasTextItem Item(FVector2D(X * UIScale, Y * UIScale), InText, Font(Size, Typeface), Color);
	Item.bCentreX = bCentre;
	Item.EnableShadow(FLinearColor(0.0f, 0.0f, 0.0f, 0.65f * Color.A), FVector2D(2.0f, 2.0f) * UIScale);
	Canvas->DrawItem(Item);
}

void AFrogLevelHUD::Panel(float X, float Y, float W, float H, const FLinearColor& Color)
{
	if (Color.A <= 0.01f)
	{
		return;
	}
	FCanvasTileItem Tile(FVector2D(X * UIScale, Y * UIScale), FVector2D(W * UIScale, H * UIScale), Color);
	Tile.BlendMode = SE_BLEND_Translucent;
	Canvas->DrawItem(Tile);
}

void AFrogLevelHUD::DrawHUD()
{
	Super::DrawHUD();

	const AFrogLevelGameMode* GameMode = GetWorld() ? GetWorld()->GetAuthGameMode<AFrogLevelGameMode>() : nullptr;
	if (!Canvas || !GameMode || !FontObject)
	{
		return;
	}

	// Lay out on a 1080-high reference screen.
	UIScale = Canvas->ClipY / 1080.0f;
	const float Width = Canvas->ClipX / UIScale;
	const float Centre = Width * 0.5f;
	const float Age = GameMode->GetLevelAge();

	// Golden flies, top left; the number pops when one is caught.
	const float Pop = FMath::Max(0.0f, 1.0f - GameMode->GetLastFlyAge() / 0.35f);
	Panel(36.0f, 32.0f, 250.0f, 82.0f, WithAlpha(Night, 0.6f));
	Text(LOCTEXT("FliesLabel", "GOLDEN FLIES"), 56.0f, 42.0f, 13.0f, Cool, false);
	Text(FText::Format(LOCTEXT("FliesCount", "{0} / {1}"), GameMode->GetFliesCollected(), GameMode->GetFliesTotal()),
		56.0f, 62.0f - Pop * 4.0f, 26.0f + Pop * 8.0f, FMath::Lerp(Gold, Warm, Pop), false);

	// Run time, top right.
	Panel(Width - 36.0f - 170.0f, 32.0f, 170.0f, 82.0f, WithAlpha(Night, 0.6f));
	Text(LOCTEXT("TimeLabel", "TIME"), Width - 186.0f, 42.0f, 13.0f, Cool, false);
	Text(Clock(GameMode->GetRunTime()), Width - 186.0f, 62.0f, 26.0f, Warm, false);

	// Level title as it starts.
	const float TitleAlpha = FadeEnvelope(Age, 5.0f, 0.8f, 1.2f);
	Text(GameMode->LevelTitle, Centre, 250.0f, 60.0f, WithAlpha(Warm, TitleAlpha), true);
	Text(GameMode->LevelSubtitle, Centre, 340.0f, 22.0f, WithAlpha(Cool, TitleAlpha), true, TEXT("Regular"));

	// Controls along the bottom for the first few seconds.
	const float ControlsAlpha = FadeEnvelope(Age, ControlsHintTime, 1.0f, 1.5f);
	Panel(Centre - 520.0f, 1080.0f - 92.0f, 1040.0f, 50.0f, WithAlpha(Night, 0.5f * ControlsAlpha));
	Text(LOCTEXT("Controls", "WASD  move     ·     Space  jump, hold to leap higher     ·     Mouse  turn the camera     ·     Wheel  zoom"),
		Centre, 1080.0f - 82.0f, 17.0f, WithAlpha(Warm, ControlsAlpha), true, TEXT("Regular"));

	// Toasts (checkpoint, hints, splashes).
	float ToastAge = 0.0f;
	float ToastDuration = 0.0f;
	const FText& Toast = GameMode->GetToast(ToastAge, ToastDuration);
	if (!Toast.IsEmpty() && !GameMode->IsLevelComplete())
	{
		const float ToastAlpha = FadeEnvelope(ToastAge, ToastDuration, 0.15f, 0.5f);
		const float Rise = (1.0f - FMath::Min(ToastAge / 0.25f, 1.0f)) * 14.0f;
		Text(Toast, Centre, 190.0f + Rise, 34.0f, WithAlpha(Warm, ToastAlpha), true);
	}

	// Finish card.
	if (GameMode->IsLevelComplete())
	{
		const float CardAlpha = FMath::Clamp((GameMode->GetFinishAge() - 0.6f) / 0.8f, 0.0f, 1.0f);
		const float Top = 300.0f;
		Panel(Centre - 330.0f, Top, 660.0f, 330.0f, WithAlpha(Night, 0.72f * CardAlpha));
		Text(LOCTEXT("Finished", "The beacon is lit!"), Centre, Top + 34.0f, 50.0f, WithAlpha(Gold, CardAlpha), true);
		Text(FText::Format(LOCTEXT("FinishFlies", "Golden flies   {0} / {1}"), GameMode->GetFliesCollected(), GameMode->GetFliesTotal()),
			Centre, Top + 130.0f, 26.0f, WithAlpha(Warm, CardAlpha), true);
		Text(FText::Format(LOCTEXT("FinishTime", "Time   {0}"), Clock(GameMode->GetRunTime())),
			Centre, Top + 172.0f, 26.0f, WithAlpha(Warm, CardAlpha), true);
		Text(FText::Format(LOCTEXT("FinishSplashes", "Splashes   {0}"), GameMode->GetSplashes()),
			Centre, Top + 214.0f, 26.0f, WithAlpha(Warm, CardAlpha), true);
		const bool bAll = GameMode->GetFliesCollected() >= GameMode->GetFliesTotal();
		Text(bAll ? LOCTEXT("FinishAll", "Every golden fly caught. What a frog!") : LOCTEXT("FinishMore", "Some golden flies are still out there..."),
			Centre, Top + 270.0f, 18.0f, WithAlpha(Cool, CardAlpha), true, TEXT("Regular"));
	}
}

#undef LOCTEXT_NAMESPACE
