// Canvas HUD for the frog levels: fly counter, run timer, the level title, controls, toasts and the
// finish card. Draws with the engine's Roboto font so it needs no UI assets.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/HUD.h"
#include "Fonts/SlateFontInfo.h"
#include "FrogLevelHUD.generated.h"

UCLASS()
class ITSAFROG_API AFrogLevelHUD : public AHUD
{
	GENERATED_BODY()

public:
	AFrogLevelHUD();

	virtual void DrawHUD() override;

	/** How long the controls line stays on screen after the level starts. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Frog Level", meta=(Units="s"))
	float ControlsHintTime = 14.0f;

private:
	UPROPERTY(Transient)
	TObjectPtr<UObject> FontObject;

	float UIScale = 1.0f;

	FSlateFontInfo Font(float Size, FName Typeface = TEXT("Bold")) const;
	void Text(const FText& InText, float X, float Y, float Size, const FLinearColor& Color, bool bCentre = false, FName Typeface = TEXT("Bold"));
	void Panel(float X, float Y, float W, float H, const FLinearColor& Color);
};
