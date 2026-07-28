// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "FrogCharacter.generated.h"

class USpringArmComponent;
class UCameraComponent;
class USkeletalMeshComponent;
class UInputAction;
class UPrimitiveComponent;
struct FInputActionValue;
class UTongueAnimInstance;

UENUM(BlueprintType)
enum class ETongueState : uint8
{
	Hidden,
	Extending,
	Attached,
	Retracting,
	Cooldown
};

UCLASS()
class ITSAFROG_API AFrogCharacter : public ACharacter
{
	GENERATED_BODY()

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta=(AllowPrivateAccess="true"))
	USpringArmComponent* CameraBoom;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta=(AllowPrivateAccess="true"))
	UCameraComponent* FollowCamera;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta=(AllowPrivateAccess="true"))
	TObjectPtr<USkeletalMeshComponent> TongueMesh;

protected:
	UPROPERTY(EditAnywhere, Category="Input")
	UInputAction* JumpAction;

	UPROPERTY(EditAnywhere, Category="Input")
	UInputAction* MoveAction;

	UPROPERTY(EditAnywhere, Category="Input")
	UInputAction* LookAction;

	UPROPERTY(EditAnywhere, Category="Input")
	UInputAction* MouseLookAction;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Tongue|Input")
	TObjectPtr<UInputAction> TongueAction;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Tongue|Configuration")
	FName TongueSocketName = TEXT("TongueSocket");

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Tongue|Configuration", meta=(ClampMin="1.0", Units="cm"))
	float MaximumTongueLength = 500.0f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Tongue|Configuration", meta=(ClampMin="0.0", Units="cm"))
	float TraceRadius = 20.0f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Tongue|Configuration", meta=(ClampMin="0.001", Units="s"))
	float ExtensionDuration = 0.12f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Tongue|Configuration", meta=(ClampMin="0.001", Units="s"))
	float RetractionDuration = 0.18f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Tongue|Configuration", meta=(ClampMin="0.0", Units="s"))
	float MaximumAttachedDuration = 0.75f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Tongue|Configuration", meta=(ClampMin="0.0", Units="s"))
	float CooldownDuration = 0.20f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Tongue|Configuration", meta=(ClampMin="0.0", Units="cm"))
	float ArcHeight = 35.0f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Tongue|Configuration", meta=(Units="cm"))
	float SideArcOffset = 0.0f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Tongue|Configuration", meta=(ClampMin="0.1"))
	float EasingExponent = 2.0f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Tongue|Configuration")
	TEnumAsByte<ECollisionChannel> TongueTraceChannel = ECC_Visibility;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Tongue|Debug")
	bool bDrawTongueDebug = false;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Tongue|Debug", meta=(ClampMin="0.0", Units="s"))
	float DebugDrawDuration = 0.0f;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Tongue|State")
	ETongueState TongueState = ETongueState::Hidden;

	void Move(const FInputActionValue& Value);
	void Look(const FInputActionValue& Value);

	UFUNCTION(BlueprintCallable, Category="Input")
	virtual void DoMove(float Right, float Forward);

	UFUNCTION(BlueprintCallable, Category="Input")
	virtual void DoLook(float Yaw, float Pitch);

	UFUNCTION(BlueprintCallable, Category="Input")
	virtual void DoJumpStart();

	UFUNCTION(BlueprintCallable, Category="Input")
	virtual void DoJumpEnd();

	UFUNCTION(BlueprintCallable, Category="Tongue")
	void LaunchTongue();

	UFUNCTION(BlueprintCallable, Category="Tongue")
	void ReleaseTongue();

	UFUNCTION(BlueprintPure, Category="Tongue")
	ETongueState GetTongueState() const { return TongueState; }

public:
	AFrogCharacter();

	virtual void BeginPlay() override;
	virtual void Tick(float DeltaTime) override;
	virtual void SetupPlayerInputComponent(class UInputComponent* PlayerInputComponent) override;

	FORCEINLINE USpringArmComponent* GetCameraBoom() const { return CameraBoom; }
	FORCEINLINE UCameraComponent* GetFollowCamera() const { return FollowCamera; }
	FORCEINLINE USkeletalMeshComponent* GetTongueMesh() const { return TongueMesh; }

protected:
	void HandleTongueStarted();
	void HandleTongueCompleted();
	void HandleTongueCanceled();

	virtual void OnTongueAttached();
	virtual void UpdateTongueAttachment();
	virtual void OnTongueReleased();

	virtual void TickTongue(float DeltaTime);
	bool SetTongueState(ETongueState NewState);
	bool CanTransitionTongueState(ETongueState From, ETongueState To) const;
	bool TryGetTongueAnimInstance(UTongueAnimInstance*& OutAnimInstance);
	bool TryGetMouthLocation(FVector& OutLocation) const;
	void UpdateTonguePose(const FVector& RootLocation, const FVector& TipLocation, float ExtensionAlpha);
	void BeginTongueRetraction();
	void CompleteTongueRetraction();
	void ValidateTongueConfiguration();
	void DrawTongueDebug(const FVector& RootLocation, const FVector& TipLocation) const;

	float TongueStateTime = 0.0f;
	FVector TongueEndpoint = FVector::ZeroVector;
	FVector RetractionStartEndpoint = FVector::ZeroVector;
	FVector TongueTargetPointLocal = FVector::ZeroVector;

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category="Tongue|State")
	TObjectPtr<AActor> TongueTargetActor;

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category="Tongue|State")
	TObjectPtr<UPrimitiveComponent> TongueTargetComponent;

	bool bWarnedMissingSocket = false;
	bool bWarnedMissingTongueMeshAsset = false;
	bool bWarnedMissingAnimInstance = false;
	bool bWarnedInvalidConfiguration = false;
	};
