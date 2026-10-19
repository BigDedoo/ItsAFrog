// Rules for a short frog platforming level: golden fly count, checkpoints and respawning,
// a run timer and the finish. AFrogLevelHUD draws the state kept here.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "FrogLevelGameMode.generated.h"

class AFrogFlyPickup;
class AFrogCheckpoint;

UCLASS()
class ITSAFROG_API AFrogLevelGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	AFrogLevelGameMode();

	virtual void BeginPlay() override;
	virtual void Tick(float DeltaTime) override;

	/** Shown when the level starts. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Frog Level")
	FText LevelTitle;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Frog Level")
	FText LevelSubtitle;

	/** Falling below this height (water, the void) sends the player back to the last checkpoint. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Frog Level", meta=(Units="cm"))
	float RespawnZ = -60.0f;

	void CollectFly(AFrogFlyPickup* Fly);
	void ActivateCheckpoint(AFrogCheckpoint* Checkpoint);
	void CompleteLevel();

	/** Fades the camera and puts the player back at the last checkpoint (or where they started). */
	UFUNCTION(BlueprintCallable, Category="Frog Level")
	void RespawnPlayer(const FText& Message);

	UFUNCTION(BlueprintCallable, Category="Frog Level")
	void ShowToast(const FText& Text, float Duration = 2.5f);

	UFUNCTION(BlueprintPure, Category="Frog Level")
	int32 GetFliesCollected() const { return FliesCollected; }
	UFUNCTION(BlueprintPure, Category="Frog Level")
	int32 GetFliesTotal() const { return FliesTotal; }
	UFUNCTION(BlueprintPure, Category="Frog Level")
	int32 GetCheckpointsReached() const { return ReachedCheckpoints.Num(); }
	UFUNCTION(BlueprintPure, Category="Frog Level")
	int32 GetSplashes() const { return Splashes; }
	UFUNCTION(BlueprintPure, Category="Frog Level")
	bool IsLevelComplete() const { return bLevelComplete; }
	/** Seconds since the level started, frozen at the finish. */
	UFUNCTION(BlueprintPure, Category="Frog Level")
	float GetRunTime() const;
	/** Seconds the level has been running (not frozen), for HUD animation. */
	float GetLevelAge() const;
	/** Seconds since the last fly was caught. */
	float GetLastFlyAge() const { return Now() - LastFlyTime; }
	/** Seconds since the level was finished (0 while it isn't). */
	float GetFinishAge() const { return bLevelComplete ? Now() - FinishTime : 0.0f; }

	/** The current toast and its age in seconds; empty when there is none. */
	const FText& GetToast(float& OutAge, float& OutDuration) const;

private:
	int32 FliesCollected = 0;
	int32 FliesTotal = 0;
	int32 Splashes = 0;
	bool bLevelComplete = false;
	bool bHasRespawn = false;
	FTransform RespawnTransform;
	float StartTime = 0.0f;
	float FinishTime = 0.0f;
	float LastRespawnTime = -100.0f;
	float LastFlyTime = -100.0f;

	FText ToastText;
	float ToastTime = 0.0f;
	float ToastDuration = 0.0f;

	UPROPERTY(Transient)
	TObjectPtr<AFrogCheckpoint> CurrentCheckpoint;

	UPROPERTY(Transient)
	TSet<TObjectPtr<AFrogCheckpoint>> ReachedCheckpoints;

	float Now() const;
};
