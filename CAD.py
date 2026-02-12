import pygame










while running:

    frame_time = clock.tick(60) / 1000.0
    accumulator += frame_time
    keys = pygame.key.get_pressed()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
             if event.key == pygame.K_SPACE:
                paused = not paused
             if event.key == pygame.K_n:
                step = True
    
        if keys[pygame.K_r]:
            score, player = reset_game()
        if keys[pygame.K_a]:
            player.velocity[0] -= velocity
        if keys[pygame.K_d]:
            player.velocity[0]  += velocity
        if keys[pygame.K_w]:
            player.velocity[1]  -= velocity
        if keys[pygame.K_s]:
            player.velocity[1] += velocity



    # FIXED SIMULATION
    while accumulator >= dt:
        if not paused or step:
            update_world(dt, balls)
            step = False
        accumulator -= dt


    # RENDER
    screen.fill("black")
    

    for ball in balls:
        ball.draw(screen)


    pygame.display.flip()

pygame.quit()