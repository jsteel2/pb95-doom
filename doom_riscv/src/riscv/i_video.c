/*
 * i_video.c
 *
 * Video system support code
 *
 * Copyright (C) 2021 Sylvain Munaut
 * All rights reserved.
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation; either version 2
 * of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 */

#include <stdint.h>
#include <string.h>

#include "doomdef.h"

#include "i_system.h"
#include "v_video.h"
#include "i_video.h"

#include "config.h"


void
I_InitGraphics(void)
{
	/* Don't need to do anything really ... */

	/* Ok, maybe just set gamma default */
	usegamma = 1;
}

void
I_ShutdownGraphics(void)
{
	/* Don't need to do anything really ... */
}


void
I_SetPalette(byte* palette)
{
	return;
}


void
I_UpdateNoBlit(void)
{
}

extern void asm_finish_update(byte* scr);

void
I_FinishUpdate (void)
{
    return asm_finish_update(screens[0]);
}


void
I_WaitVBL(int count)
{
}


void
I_ReadScreen(byte* scr)
{
	memcpy(
		scr,
		screens[0],
		SCREENHEIGHT * SCREENWIDTH
	);
}


#if 0	/* WTF ? Not used ... */
void
I_BeginRead(void)
{
}

void
I_EndRead(void)
{
}
#endif
