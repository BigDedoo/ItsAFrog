// Gameplay pieces for the frog platforming levels: golden flies, checkpoints, the goal beacon,
// bounce mushrooms, hazards and tutorial hints. Each is a trigger box that reacts to the player's pawn
// and reports to AFrogLevelGameMode; meshes are assigned per instance by the level builder.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "FrogLevelActors.generated.h"

class UBoxComponent;
class UPointLightComponent;
class UStaticMeshComponent;
class ACharacter;
class AFrogLevelGameMode;

/** Trigger box that calls OnPlayerEnter when the locally controlled player's pawn walks in. */
UCLASS(Abstract)
class ITSAFROG_API AFrogLevelTrigger : public AActor
{
	GENERATED_BODY()

public:
	AFrogLevelTrigger();

	UBoxComponent* GetTrigger() const { return Trigger; }

protected:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Frog Level", meta=(AllowPrivateAccess="true"))
	TObjectPtr<UBoxComponent> Trigger;

	virtual void NotifyActorBeginOverlap(AActor* OtherActor) override;
	virtual void OnPlayerEnter(ACharacter* Player) {}

	AFrogLevelGameMode* GetFrogGameMode() const;
};

/** A golden fly: bobs and spins in place, and counts towards the level's total when touched. */
UCLASS()
class ITSAFROG_API AFrogFlyPickup : public AFrogLevelTrigger
{
	GENERATED_BODY()

public:
	AFrogFlyPickup();

	virtual void Tick(float DeltaTime) override;

	bool IsCollected() const { return bCollected; }

protected:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Frog Level")
	TObjectPtr<UStaticMeshComponent> Mesh;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Frog Level")
	TObjectPtr<UPointLightComponent> Glow;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Frog Level", meta=(Units="cm"))
	float BobHeight = 10.0f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Frog Level", meta=(Units="deg"))
	float SpinSpeed = 120.0f;

	virtual void BeginPlay() override;
	virtual void OnPlayerEnter(ACharacter* Player) override;

private:
	bool bCollected = false;
	float Age = 0.0f;
	float CollectedAge = 0.0f;
	float Phase = 0.0f;
	FVector MeshBaseLocation = FVector::ZeroVector;
	FVector MeshBaseScale = FVector::OneVector;
	float GlowBaseIntensity = 0.0f;
};

/** Sets the player's respawn point and lights up the first time the player reaches it. */
UCLASS()
class ITSAFROG_API AFrogCheckpoint : public AFrogLevelTrigger
{
	GENERATED_BODY()

public:
	AFrogCheckpoint();

	virtual void Tick(float DeltaTime) override;

	/** Where the player reappears: the actor's location raised by RespawnHeight, facing the actor's forward. */
	FTransform GetRespawnTransform() const;

protected:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Frog Level")
	TObjectPtr<UStaticMeshComponent> Mesh;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Frog Level")
	TObjectPtr<UPointLightComponent> Light;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Frog Level", meta=(Units="cm"))
	float RespawnHeight = 80.0f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Frog Level")
	FLinearColor IdleColor = FLinearColor(0.45f, 0.62f, 1.0f);

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Frog Level")
	FLinearColor ActiveColor = FLinearColor(1.0f, 0.62f, 0.25f);

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Frog Level", meta=(Units="lm"))
	float ActiveIntensity = 1200.0f;

	virtual void OnPlayerEnter(ACharacter* Player) override;

private:
	bool bActive = false;
	float ActiveAge = 0.0f;
	float IdleIntensity = 0.0f;
};

/** The level's end: lights its beacon and finishes the level when the player arrives. */
UCLASS()
class ITSAFROG_API AFrogGoal : public AFrogLevelTrigger
{
	GENERATED_BODY()

public:
	AFrogGoal();

	virtual void Tick(float DeltaTime) override;

protected:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Frog Level")
	TObjectPtr<UStaticMeshComponent> Mesh;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Frog Level")
	TObjectPtr<UPointLightComponent> Beacon;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Frog Level", meta=(Units="lm"))
	float LitIntensity = 7000.0f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Frog Level", meta=(Units="s"))
	float LightUpTime = 1.5f;

	virtual void BeginPlay() override;
	virtual void OnPlayerEnter(ACharacter* Player) override;

private:
	bool bLit = false;
	float LitAge = 0.0f;
	float UnlitIntensity = 0.0f;
};

/** A springy mushroom cap: launches the player upwards and squashes its mesh. */
UCLASS()
class ITSAFROG_API AFrogBouncePad : public AFrogLevelTrigger
{
	GENERATED_BODY()

public:
	AFrogBouncePad();

	virtual void Tick(float DeltaTime) override;

protected:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Frog Level")
	TObjectPtr<UStaticMeshComponent> Mesh;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Frog Level", meta=(Units="cm/s"))
	float LaunchSpeed = 1100.0f;

	virtual void BeginPlay() override;
	virtual void OnPlayerEnter(ACharacter* Player) override;

private:
	float SquashAge = -1.0f;
	FVector MeshBaseScale = FVector::OneVector;
};

/** Sends the player back to the last checkpoint (thorns, deep water). */
UCLASS()
class ITSAFROG_API AFrogRespawnVolume : public AFrogLevelTrigger
{
	GENERATED_BODY()

public:
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Frog Level")
	FText Message;

protected:
	virtual void OnPlayerEnter(ACharacter* Player) override;
};

/** Shows a tutorial hint on the HUD the first time the player walks in. */
UCLASS()
class ITSAFROG_API AFrogHintVolume : public AFrogLevelTrigger
{
	GENERATED_BODY()

public:
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Frog Level", meta=(MultiLine="true"))
	FText Message;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Frog Level", meta=(Units="s"))
	float Duration = 4.0f;

protected:
	virtual void OnPlayerEnter(ACharacter* Player) override;

private:
	bool bShown = false;
};
